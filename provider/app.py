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

app = Chalice(app_name='provider')

dynamo = boto3.resource('dynamodb')
runs_table = dynamo.Table(RUNS_TABLE)

s3 = boto3.resource('s3', region_name='us-west-2')
bucket = s3.Bucket(BUCKET)
remap_data = {}

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
    try:
        time_index = list(nc.variables['time']).index(int(time_arg))
    except ValueError as e:
        return None
    return time_index


def load_remap_data(source_grid, target_grid):
    logger.info('Loading remap data from {} to {}'.format(source_grid, target_grid))
    filename = 'remap_data_{}_to_{}.pickle'.format(source_grid, target_grid)
    key = 'remap-data/'+filename
    pickle_file = '/tmp/'+filename
    obj = s3.Object(BUCKET, key)
    try:
        obj.download_file(pickle_file)
        with open(pickle_file, 'r') as fd:
            tmp = pickle.load(fd)
            remap_data[(source_grid, target_grid)] = tmp
        # FIXME: save remapped version back to S3
    except ClientError as e:
        logger.info(e)
        logger.info('Remapping file from {} to {} not found'.format(source_grid, target_grid))
    except e:
        logger.info(e)

# load_remap_data('4x5', 'C40962')


def remap_variable(source_grid, target_grid, data):
    logger.info('remap variable {} {}'.format(source_grid, target_grid))
    if (source_grid, target_grid) not in remap_data:
        load_remap_data(source_grid, target_grid)
    if (source_grid, target_grid) not in remap_data:
        return None
    rd = remap_data[(source_grid, target_grid)]

    output = [0] * rd['target_size']
    var_slice = data.reshape([data.shape[0] * data.shape[1], 1])
    for gi in range(1, rd['target_size']):
        if gi not in rd['a_to_s'] or gi not in rd['a_to_b']:
            logger.info('grid {} not found'.format(gi))
            continue
        try:
            w = rd['a_to_s'][gi]
            b_inds = rd['a_to_b'][gi]
            v = var_slice[b_inds][:]
            v = v.reshape((v.shape[0],))
            a = rd['b_areas'][gi]
            output[gi] = np.dot(np.multiply(v,a),w) / rd['area_a'][gi]
        except IndexError as e:
            logger.info('error {}'.format(gi))
        except e:
            logger.info(e)
    return output


@app.route('/run/{run_id}/variable/{modelname}/{varname}/data')
def variable_data(run_id, modelname, varname):
    nc = load_nc_file(run_id, modelname, varname)
    
    params = app.current_request.query_params
    target_grid = params.get('remap', None)
    logger.info('target grid {}'.format(target_grid))      

    time_arg = params.get('time', None)
    if not time_arg:
        return {'error': 'Must supply time param'}
    
    time_index = get_time_index(nc, time_arg)
    if not time_index:
        return {'error': 'Time {} not found in {} variable {} {}'.format(
            time_arg, run_id, modelname, varname)}

    data = nc.variables[varname].data
    if len(data.shape) == 4:
        level_arg = params.get('time', 0)
        data = data[:,level_arg,:,:]
    data_slice = data[time_index,:,:]
    source_grid = '4x5' #FIXME infer from data
    if target_grid:
        as_list = remap_variable(source_grid, target_grid, data_slice)
        if not as_list:
            return {'error': 'Remap option {} not recognized'.format(remap_arg)}
    else:
        as_list = [[float(f) for f in a] for a in list(data_slice)]

    return {
        'run_id': run_id,
        'model': modelname,
        'variable': varname,
        'time': time_arg,
        'data': as_list
    }


def varname_for_key(key):
    return key.split('/')[-1].split('.')[0][3:]
