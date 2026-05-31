Load test run time: 15 minutes
DB CPU utilization at peak load: 97+%
Instance count: 2, auto-scaling did trigger, but not because of the load of the API EC2 instances

Observations:
- The database instance is under heavy load, with CPU utilization reaching constant 97+% during this load
- Auto-scaling of EC2 instances did trigger in all 3 runs, this was due to the healthcheck endpoint timing out as the application was not able to respond to requests
- However, the RDS instance is still bottle-necking the performance, and adding more instances does not help to reduce the load on the database

- run 2 is only 13 minutes long, as locust was killed by OOM killer on my local machine which was generating the load.
