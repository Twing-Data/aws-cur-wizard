import boto3
import os
import pytest

from botocore.exceptions import NoCredentialsError, PartialCredentialsError, ClientError
from dotenv import load_dotenv


def test_env_file_present():
    assert os.path.isfile('.env')

def test_env_vars_defined():
    load_dotenv()
    assert os.getenv('aws_access_key_id')
    assert os.getenv('aws_secret_access_key')
    assert os.getenv('aws_region')
    assert os.getenv('bucket_name')
    assert os.getenv('s3_input_data_dir')
    assert os.getenv('input_data_type')
    assert os.getenv('normalized_data_dir')
    assert os.getenv('rill_project_path')

def test_aws_credentials_validity():
    load_dotenv()
    client = boto3.client(
        "sts",
        aws_access_key_id = os.getenv('aws_access_key_id'),
        aws_secret_access_key = os.getenv('aws_secret_access_key'),
        region_name = os.getenv('aws_region')
    )

    try:
        # This call does not require specific permissions, just valid credentials
        response = client.get_caller_identity()

        # Check that we received expected fields
        assert "Account" in response
        assert "UserId" in response
        assert "Arn" in response

    except NoCredentialsError:
        pytest.fail("No credentials were provided.")

    except PartialCredentialsError:
        pytest.fail("Incomplete AWS credentials provided.")

    except ClientError as e:
        if e.response['Error']['Code'] == 'InvalidClientTokenId':
            pytest.fail("Invalid AWS access key ID or secret access key.")
        else:
            pytest.fail(f"Unexpected AWS client error: {e}")

@pytest.fixture(scope="module")
def s3_client():
    load_dotenv()
    return boto3.client(
        "s3",
        aws_access_key_id = os.getenv('aws_access_key_id'),
        aws_secret_access_key = os.getenv('aws_secret_access_key'),
        region_name = os.getenv('aws_region')
    )

def test_bucket_exists(s3_client):
    load_dotenv()
    bucket_name = os.getenv('bucket_name')
    try:
        s3_client.head_bucket(Bucket=bucket_name)
        bucket_exists = True
    except ClientError:
        bucket_exists = False
    assert bucket_exists, f"Bucket '{bucket_name}' does not exist or access is denied."

def test_directory_exists(s3_client):
    load_dotenv()
    bucket_name = os.getenv('bucket_name')
    s3_input_data_dir = os.getenv('s3_input_data_dir')

    response = s3_client.list_objects_v2(Bucket=bucket_name, Prefix=s3_input_data_dir, MaxKeys=1)
    directory_exists = "Contents" in response
    assert directory_exists, f"Directory '{s3_input_data_dir}' not found in bucket '{bucket_name}'."

def test_file_type():
    """
    Test that user has specified an acceptable file type
    """
    load_dotenv()
    assert os.getenv('input_data_type') in ['parquet', 'csv']

def test_s3_directory_contains_python_files(s3_client):
    """
    Test that an S3 directory contains at least one file with the expected extension, e.g. '.parquet', '.csv', etc
    """
    load_dotenv()
    bucket_name = os.getenv('bucket_name')
    s3_input_data_dir = os.getenv('s3_input_data_dir')
    input_data_type = os.getenv('input_data_type')

    try:
        response = s3_client.list_objects_v2(Bucket=bucket_name, Prefix=s3_input_data_dir)
    except ClientError as e:
        pytest.fail(f"Failed to list S3 objects: {e}")

    # Check if the directory exists and contains files
    if "Contents" not in response:
        pytest.fail(f"No objects found under s3://{bucket_name}/{s3_input_data_dir}")

    # Extract keys and filter for .py files
    python_files = [
        obj["Key"] for obj in response["Contents"]
        if obj["Key"].endswith(f".{input_data_type}")
    ]

    assert python_files, f"No files of type {input_data_type} found under s3://{bucket_name}/{s3_input_data_dir}"