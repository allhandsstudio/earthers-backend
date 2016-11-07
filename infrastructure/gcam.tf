resource "aws_dynamodb_table" "GCAM_Runs" {
	name = "${var.gcam_runs_table}"
	read_capacity = 1
	write_capacity = 1
	hash_key = "runId"
	# range_key = "Timestamp"
	stream_enabled = true
	stream_view_type = "NEW_IMAGE"
	attribute {
		name = "runId"
		type = "S"
	}
	attribute {
		name = "runStatus"
		type = "S"
	}
	attribute {
		name = "createdAt"
		type = "S"
	}
	global_secondary_index {
		name = "StatusIndex"
		hash_key = "runStatus"
		range_key = "createdAt"
		read_capacity = 1
		write_capacity = 1
		projection_type = "ALL"
	}
}

resource "aws_s3_bucket" "gcam_runs" {
    bucket = "gcam-runs.earthers.studio"
}