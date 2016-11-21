import time
import datetime
import gzip
import os
import errno
import shutil
from xml.etree.cElementTree import iterparse
import subprocess
import StringIO

import boto3
from botocore.exceptions import ClientError

DELAY = 10
RUN_TABLE = 'GCAM_Runs'
RUN_BUCKET = 'gcam-runs.earthers.studio'
INPUT_DATA_BUCKET = 'gcam-input-data'
PENDING_STATUS = 'pending'

dynamo = boto3.client('dynamodb')
s3 = boto3.client('s3')


def mkdir_p(path):
	try:
		os.makedirs(path)
	except OSError as exc:
		if exc.errno == errno.EEXIST and os.path.isdir(path):
			pass
		else:
			raise


def get_next_job():
	result = dynamo.query(
		TableName=RUN_TABLE,
		IndexName='StatusIndex',
		Select='ALL_ATTRIBUTES',
		KeyConditionExpression='runStatus=:v1',
		ExpressionAttributeValues={ ':v1': { 'S': PENDING_STATUS } },
		Limit=1
		)
	if result['Count'] >= 1:
		item = result['Items'][0]
		s3_bucket = item['s3Location']['S'].split('/')[0]
		s3_root = '/'.join(item['s3Location']['S'].split('/')[1:])
		return {
			'run_id': item['runId']['S'],
			's3_root': s3_root,
			's3_bucket': s3_bucket
		}
	else:
		return None


def set_run_status(run_id, status, prevStatus):
	"""
	Change run status and updated timestamp IFF a previous status holds
	"""
	now = datetime.datetime.now().isoformat()
	resp=dynamo.update_item(
		TableName=RUN_TABLE,
		Key={ 'runId': { 'S': run_id  } } ,
		UpdateExpression='SET #rs = :status, #ua = :now',
		ConditionExpression='#rs = :prevStatus',
		ExpressionAttributeValues={ 
			':status': { 'S': status },
			':prevStatus': { 'S': prevStatus },
			':now': { 'S': now }
		},
		ExpressionAttributeNames={
			'#rs': 'runStatus',
			'#ua': 'updatedAt'
		},
		ReturnValues='UPDATED_NEW'
	)
	success = resp['Attributes']['runStatus']['S'] == status
	if not success:
		print "failed to change status from {} to {} for {}".format(prevStatus, status, run_id)
	return success


def get_input_filenames(config_file):
	"""
	Parse the config file to find all of the input filenames that will be needed
	"""
	doc = iterparse(config_file, ('start', 'end'))
	for event, elem in doc:
		if event == 'end':
			if elem.tag == 'ScenarioComponents':
				filenames = [c.text[2:] for c in elem if c.attrib.get('name', '') is not 'earthers_scenario']
				return filenames


def s3_to_file(bucket, key, filename):
	s = ''
	try:
		result = s3.get_object(Bucket=bucket, Key=key)
		s = result['Body'].read()
	except ClientError as e:
		print 's3 key {} not found'.format(key)

	mkdir_p(os.path.dirname(filename))
	with open(filename, 'wb') as fd:
		fd.write(s)


def s3_from_file(filename, bucket, key):
	try:
		with open(filename, 'rb') as fd:
			s3.put_object(
				Bucket=bucket,
				Key=key,
				Body=fd.read()
				)
	except ClientError as e:
		print 'Error putting to s3: {}'.format(e)


def run():
	while True:
		next_job = get_next_job()
		if next_job:
			run_id = next_job['run_id']
			s3_root = next_job['s3_root']

			if not set_run_status(run_id, 'running', 'pending'):
				continue

			print 'Processing run {}'.format(run_id)
			# prepare local temp space
			run_dir = '/tmp/{}'.format(run_id)
			os.mkdir(run_dir)

			config_file = '{}/configuration.xml'.format(run_dir)
			logconf_file = '{}/log_conf.xml'.format(run_dir)
			modeltime_file = '{}/modeltime.xml'.format(run_dir)

			# copy configuration files to run-specific location
			shutil.copy('configuration.xml', config_file)
			shutil.copy('log_conf.xml', logconf_file)
			shutil.copy('modeltime.xml', modeltime_file)
			shutil.copytree('/climate', '{}/climate'.format(run_dir))

			# fetch base input files
			input_filenames = get_input_filenames(config_file)
			for f in input_filenames:
				print('fetching input file {}'.format(f))
				s3_to_file(INPUT_DATA_BUCKET, f, '{}/{}'.format(run_dir, f))

			# fetch scenario file
			s3_to_file(
				next_job['s3_bucket'], 
				'{}/config/scenario.xml'.format(next_job['s3_root']), 
				'{}/earthers_scenario.xml'.format(run_dir))

			# execute run
			print 'running {}'.format(config_file)
			error = False
			try:
				os.chdir(run_dir)
				output = subprocess.check_output(
					['/gcam-core/exe/gcam.exe'], shell=True, stderr=subprocess.STDOUT)
				print 'gcam finished normally'
				with open('gcam_output.txt', 'wb') as fd:
					fd.write(output)
			except subprocess.CalledProcessError as e:
				print 'gcam finished with error'
				error = True
				with open('gcam_output.txt', 'wb') as fd:
					fd.write(e.output)

			if error:
				set_run_status(run_id, 'gcam_error', 'running')
				s3_from_file('./gcam_output.txt', RUN_BUCKET, '{}/output/console.txt'.format(s3_root))
			else:
				# write results to s3
				with gzip.open('./output.xml.gz', 'wb') as gz:
					with open('./output.xml', 'rb') as fd:
						gz.write(fd.read())
				s3_from_file('./output.xml.gz', RUN_BUCKET, '{}/output/output.xml.gz'.format(s3_root))
				s3_from_file('./gcam_output.txt', RUN_BUCKET, '{}/output/console.txt'.format(s3_root))
				s3_from_file('./logs/gcam-hector-outputstream.csv', RUN_BUCKET, '{}/output/hector-output.csv'.format(s3_root))
				s3_from_file('./outFile.csv', RUN_BUCKET, '{}/output/output.csv'.format(s3_root))

				set_run_status(run_id, 'gcam_complete', 'running')

				shutil.rmtree(run_dir)

		else:
			print 'No pending runs found; sleeping'
			time.sleep(DELAY)


if __name__ == '__main__':
	run()