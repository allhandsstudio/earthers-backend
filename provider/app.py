# To deploy this to Lambda using chalice, numpy and pupynere must be pip installed
# on a Linux machine (in a virtualenv), and the python distribution files copied into
# the chalice venv

from chalice import Chalice
import boto3
from boto3.dynamodb.conditions import Key, Attr
from botocore.exceptions import ClientError
import sys
from pupynere import netcdf_file
import logging
import os.path
import pickle
import numpy as np

logger = logging.getLogger()
logger.setLevel(logging.INFO)

RUNS_TABLE = 'CESM_Runs'
BUCKET = 'cesm-output-data'
RUNS_ATTRIBUTES = [
    'InstanceId',
    'CreatedTime',
    'COMP_ATM',
    'COMP_LND',
    'COMP_OCN',
    'COMP_ICE',
    'ATM_GRID',
    'OCN_GRID',
    'ICE_GRID',
    'LND_GRID',
    'RUN_STARTDATE',
    'RUN_TYPE',
    'CONTINUE_RUN'    
]

MODELS = ['atm', 'lnd', 'ocn', 'ice', 'rof']

SOURCE_GRIDS = {
    3312: '4x5',
    13824: '1.9x2.5',
    55296: '0.9x1.25'
}


app = Chalice(app_name='provider')
app.debug = True

dynamo = boto3.resource('dynamodb')
runs_table = dynamo.Table(RUNS_TABLE)

s3 = boto3.resource('s3', region_name='us-west-2')
bucket = s3.Bucket(BUCKET)
remap_data = {}
new_remap_weights = {}

@app.route('/')
def index():
    return {'hello': 'world'}


@app.route('/runs')
def runs():
    """
    Return information about all runs, possibly filtered via url params
    """
    response = runs_table.scan(ProjectionExpression=','.join(RUNS_ATTRIBUTES))
    if response['ResponseMetadata']['HTTPStatusCode'] == 200:
        runs = {}
        for run in response['Items']:
            if run['InstanceId'] in runs:
                if run['CreatedTime'] > runs[run['InstanceId']]['CreatedTime']:
                    runs[run['InstanceId']] = run
            else:
                runs[run['InstanceId']] = run
        return runs.values()
    else:
        return {'status_code': response['ResponseMetadata']['HTTPStatusCode']}


@app.route('/run/{run_id}')
def run(run_id):
    """
    Return information about a specific run, including its CESM configuration and its output
    """
    try:
        response = runs_table.query(
            KeyConditionExpression=Key('InstanceId').eq(run_id),
            ScanIndexForward=False, Limit=1)
        if 'Items' not in response or len(response['Items']) == 0:
            return {}
        run_info = response['Items'][0]
        output = []
        for model in MODELS:
            s3Prefix = '{}/output/{}'.format(run_id, model)
            s3objs = bucket.objects.filter(Prefix=s3Prefix)
            output.extend([[model, varname_for_key(os.key), os.key] for os in s3objs if os.key.endswith(".nc")])
        return {'run_info': run_info, 'output': output}
    except ClientError, e:
        return {'error': str(e)}
    except e:
        return os.exc_info()


def get_dimension_info(nc, dim_name):
    if dim_name in nc.variables:
        dim = nc.variables[dim_name]
        return {
            'values': list(dim.data),
            'units': dim.units,
            'long_name': dim.long_name
        }
    else:
        return None


def load_nc_file(run_id, modelname, varname):
    key = '{}/output/{}/ts_{}.nc'.format(run_id, modelname, varname)
    filename = '/tmp/{}_{}_{}_varname.nc'.format(run_id, modelname, varname)
    # if not os.path.isfile(filename):
    obj = s3.Object(BUCKET, key)
    obj.download_file(filename)
    nc = netcdf_file(filename, 'r')
    return nc


@app.route('/run/{run_id}/variable/{modelname}/{varname}/info')
def variable_info(run_id, modelname, varname):
    nc = load_nc_file(run_id, modelname, varname)
    return {
        'run_id': run_id,
        'model': modelname,
        'variable': varname,
        # 'last_modified': str(obj.last_modified),
        'time': get_dimension_info(nc, 'time'),
        'lat': get_dimension_info(nc, 'lat'),
        'lon': get_dimension_info(nc, 'lon'),
        'lev': get_dimension_info(nc, 'lev')
    }


def get_time_index(nc, time_arg):
    int_time = int(time_arg)
    times = [int(t) for t in list(nc.variables['time'])]
    try:
        time_index = times.index(int(time_arg))
    except ValueError as e:
        # be forgiving, and return smallest time >= given time
        for i in range(len(times)):
            if int_time <= times[i]:
                logger.info('returning {} for {}'.format(times[i], time_arg))
                return i
        return None

    return time_index


def load_remap_data(source_grid, target_grid):
    logger.info('Loading remap data from {} to {}'.format(source_grid, target_grid))
    filename = 'remap_weights_{}_to_{}.pickle'.format(source_grid, target_grid)
    key = 'remap-data/'+filename
    pickle_file = '/tmp/'+filename
    obj = s3.Object(BUCKET, key)
    try:
        obj.download_file(pickle_file)
        with open(pickle_file, 'r') as fd:
            tmp = pickle.load(fd)
            remap_data[(source_grid, target_grid)] = tmp
    except ClientError as e:
        logger.info(e)
        logger.info('Remapping file from {} to {} not found'.format(source_grid, target_grid))
    except e:
        logger.info(e)


def remap_variable(source_grid, target_grid, data):
    logger.info('remap variable {} {}'.format(source_grid, target_grid))
    if (source_grid, target_grid) not in remap_data:
        load_remap_data(source_grid, target_grid)
    if (source_grid, target_grid) not in remap_data:
        return None

    rd = remap_data[(source_grid, target_grid)]
    I = rd['I']
    W = rd['W']
    N = len(I)

    data = data.reshape((data.shape[0]*data.shape[1],))
    out = [np.dot(data[I[j]], W[j]) for j in range(N)]

    return out


def get_cache_key(run_id, modelname, varname, levels, time, grid):
    key = 'cached-data/run-{}/model-{}/var-{}/time-{}'.format(
        run_id, modelname.lower(), varname.lower(), str(int(time)))
    if len(levels) == 1:
        key = key+'/level-'+str(levels[0])
    if grid:
        key = key+'/grid-'+grid
    return key


def load_cached(run_id, modelname, varname, levels, time, grid):
    key = get_cache_key(run_id, modelname, varname, levels, time, grid)

    cache_file = '/tmp/'+key.replace('/','_')
    obj = s3.Object(BUCKET, key)
    try:
        obj.download_file(cache_file)
    except ClientError as e:
        # not in cache
        return None

    with open(cache_file, 'r') as fd:
         x = pickle.load(fd)
         return x


def save_cached(run_id, modelname, varname, levels, time, grid, data):
    key = get_cache_key(run_id, modelname, varname, levels, time, grid)
    cache_file = '/tmp/'+key.replace('/','_')
    logger.info('save {} to {}'.format(cache_file, key))

    with open(cache_file, 'wb') as fd:
        pickle.dump(data, fd, pickle.HIGHEST_PROTOCOL)

    s3.meta.client.upload_file(cache_file, BUCKET, key)


@app.route('/run/{run_id}/variable/{modelname}/{varname}/data')
def variable_data(run_id, modelname, varname):
    params = app.current_request.query_params
    target_grid = params.get('remap', None)
    logger.info('target grid {}'.format(target_grid))      

    time_arg = params.get('time', None)
    if not time_arg:
        return {'error': 'Must supply time param'}

    level_arg = params.get('level', None)
    levels = [0]
    if level_arg:
        levels[0] = int(level_arg)

    cached = None
    if target_grid:
        cached = load_cached(run_id, modelname, varname, levels, time_arg, target_grid)

    as_lists = []

    if cached:
        logger.info('{} {} {} loaded from cache'.format(run_id, modelname, varname))
        as_lists = cached
    else:
        logger.info('{} {} {} not found in cache'.format(run_id, modelname, varname))
        nc = load_nc_file(run_id, modelname, varname)

        time_index = get_time_index(nc, time_arg)
        if time_index == None:
            return {'error': 'Time {} not found in {} variable {} {}'.format(
                time_arg, run_id, modelname, varname)}

        data = nc.variables[varname].data
        if len(data.shape) == 4:
            if level_arg:
                data = data[:,levels[0],:,:]
            else:
                levels = range(data.shape[1])

        for level in levels:
            if len(levels) == 1:
                level_data = data
            else:
                level_data = data[:,level,:,:]
            data_slice = level_data[time_index,:,:]
            num_cells = np.prod(data_slice.shape)
            source_grid = SOURCE_GRIDS.get(num_cells, None)

            if target_grid:
                as_list = remap_variable(source_grid, target_grid, data_slice)
                as_lists.append(as_list)
                if not as_list:
                    return {'error': 'Remap option {} not recognized'.format(target_grid)}
            else:
                as_lists.append([[float(f) for f in a] for a in list(data_slice)])
        if len(levels) == 1:
            as_lists = as_lists[0]

        save_cached(run_id, modelname, varname, levels, time_arg, target_grid, as_lists)
    
    return {
        'run_id': run_id,
        'model': modelname,
        'variable': varname,
        'time': time_arg,
        'data': as_lists
    }


def varname_for_key(key):
    return key.split('/')[-1].split('.')[0][3:]
