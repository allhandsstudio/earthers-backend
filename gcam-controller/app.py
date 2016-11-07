from uuid import uuid4
import datetime

from chalice import Chalice
import boto3
import base64

app = Chalice(app_name='gcam-controller')
app.debug = True

dynamo = boto3.client('dynamodb')
s3 = boto3.client('s3')
RUN_TABLE = 'GCAM_Runs'
RUN_BUCKET = 'gcam-runs.earthers.studio'

@app.route('/')
def index():
    return {'msg': 'GCAM controller endpoint'}

@app.route('/runs', methods=['GET', 'POST'], cors=True)
def runs():
	request = app.current_request
	if request.method == 'GET':
		# return a summary of most runs
		status = app.current_request.query_params.get('status', 'pending')
		limit = int(app.current_request.query_params.get('limit', 20))
		result = dynamo.query(
			TableName=RUN_TABLE,
			IndexName='StatusIndex',
			Select='ALL_ATTRIBUTES',
			KeyConditionExpression='runStatus=:v1',
			ExpressionAttributeValues={ ':v1': { 'S': status } },
			Limit=limit,
			ScanIndexForward=False
			)
		return [{ 'run_id': x['runId']['S'], 'created_at': x['createdAt']['S'] } for x in result['Items']]

	elif request.method == 'POST':
		# create a new run
		run_id = str(uuid4())
		now = datetime.datetime.now().isoformat()
		data = app.current_request.json_body
		body_type = data.get('body_type', 'inline')
		if body_type == 'inline':
			scenario_data = data.get('scenario', '')
			try:
				scenario_xml = base64.b64decode(scenario_data)
				s3.put_object(
					Bucket=RUN_BUCKET,
					Key='{}/config/scenario.xml'.format(run_id),
					Body=scenario_xml)
			except TypeError, e:
				return { 'err': 'Problem reading scenario: {}'.format(str(e)) }
		elif body_type == 's3':
			return { 'err': 'body_type s3 not yet implemented' }
		else:
			return { 'err': 'body_type {} not recognized'.format(body_type) }

		resp = dynamo.put_item(
			TableName=RUN_TABLE,
			Item={
				'runId': { 'S': run_id },
				'createdAt': { 'S': now },
				'updatedAt': { 'S': now },
				'runStatus': { 'S': 'pending' },
				'message': { 'S': 'newly created'},
				's3Location': { 'S': '{}/{}'.format(RUN_BUCKET, run_id)}
			})
		return {'msg': 'Run {} created'.format(run_id)}


@app.route('/runs/{run_id}', methods=['GET', 'POST'], cors=True)
def run(run_id):
	pass

# The view function above will return {"hello": "world"}
# whenver you make an HTTP GET request to '/'.
#
# Here are a few more examples:
#
# @app.route('/hello/{name}')
# def hello_name(name):
#    # '/hello/james' -> {"hello": "james"}
#    return {'hello': name}
#
# @app.route('/users', methods=['POST'])
# def create_user():
#     # This is the JSON body the user sent in their POST request.
#     user_as_json = app.json_body
#     # Suppose we had some 'db' object that we used to
#     # read/write from our database.
#     # user_id = db.create_user(user_as_json)
#     return {'user_id': user_id}
#
# See the README documentation for more examples.
#
