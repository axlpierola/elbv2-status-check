import boto3
from datetime import datetime, timedelta
import csv

# List of regions to check
regions = ['us-east-1', 'us-west-2']
# Define the period
period = 60 * 60 * 24 * 30  # 30 days

# Define the current time
end_time = datetime.utcnow()
# Define the start time
start_time = end_time - timedelta(seconds=period)

# Function to identify the load balancer type
def identify_load_balancer_type(elbv2, arn):
    response = elbv2.describe_load_balancers(
        LoadBalancerArns=[
            arn,
        ]
    )
    if 'LoadBalancers' in response and len(response['LoadBalancers']) > 0:
        return response['LoadBalancers'][0]['Type']
    else:
        return None

# Create a CSV file
with open('load_balancer_status.csv', 'w', newline='') as file:
    writer = csv.writer(file)
    writer.writerow(["Region", "LoadBalancerName", "Type", "Status"])

    # Iterate over each region
    for region in regions:
        # Create a CloudWatch and ELB client
        cloudwatch = boto3.client('cloudwatch', region_name=region)
        elbv2 = boto3.client('elbv2', region_name=region)

        # Get all load balancers in the region
        response = elbv2.describe_load_balancers()
        for lb in response['LoadBalancers']:
            # Parse the LoadBalancerName and LoadBalancerId from the ARN
            lb_name_id = lb['LoadBalancerArn'].split(':')[-1].split('/')[1:]
            lb_name_id = '/'.join(lb_name_id)

            lb_type = identify_load_balancer_type(elbv2, lb['LoadBalancerArn'])

            # Decide the namespace and metric name based on the LB type
            if lb_type == 'network':
                namespace = 'AWS/NetworkELB'
                metric_name = 'ActiveFlowCount'
            else:
                namespace = 'AWS/ApplicationELB'
                metric_name = 'RequestCount'

            # Get metrics for the load balancer
            metrics_response = cloudwatch.get_metric_statistics(
                Namespace=namespace,
                MetricName=metric_name,
                Dimensions=[
                    {
                        'Name': 'LoadBalancer',
                        'Value': lb_name_id
                    },
                ],
                StartTime=start_time,
                EndTime=end_time,
                Period=period,
                Statistics=['Sum'],
            )

            # If there were any requests, the LB is active
            if metrics_response['Datapoints']:
                writer.writerow([region, lb['LoadBalancerName'], lb_type, "Active"])
            else:
                writer.writerow([region, lb['LoadBalancerName'], lb_type, "Inactive"])
