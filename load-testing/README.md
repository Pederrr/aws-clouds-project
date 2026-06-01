# Setup virtual environment and install dependencies

- Create a Python virtual environment and activate it:
```
$ python3 -m venv venv
$ source venv/bin/activate
```
- Install the required dependencies:
```
$ pip install -r requirements.txt
```

# Seeding the DB

- The `dump_file.sqp` file contains the SQL dump for quicker seeding of the DB. It was generated using the `seed_api.py` script.
- Create EC2 instance in the `booklogr-vpc`, with the `BooklogrAPI` security group, and the `vockey` key pair.
- Copy the `dump_file.sql` file to the EC2 instance:
```
$ scp -i /path/to/labsuser.pem dump_file.sql ec2-user@<EC2_PUBLIC_IP>:/home/ec2-user/
```
- SSH into the EC2 instance:
```
$ ssh -i /path/to/labsuser.pem ec2-user@<EC2_PUBLIC_IP>
```
- Install psql client:
```
$ sudo yum install postgresql18 -y
```
- Setup the db connection:
```
$ curl -o global-bundle.pem https://truststore.pki.rds.amazonaws.com/global/global-bundle.pem
$ export RDSHOST="<DB_ENDPOINT>"
```
- Drop the data in the database:
```
$ psql "host=$RDSHOST port=5432 dbname=booklogr user=postgres sslmode=verify-full sslrootcert=./global-bundle.pem" -c "DROP TABLE IF EXISTS alembic_version, books, files, notes, profiles, reading_sessions, revoked_tokens, tasks, user_settings, users, verification CASCADE;"
```
- Import the SQL dump into the database:
```
$ psql "host=$RDSHOST port=5432 dbname=booklogr user=postgres sslmode=verify-full sslrootcert=./global-bundle.pem" -f dump_file.sql
```

# Running the Load Test

- Make sure the followed the steps to create Python venv and install dependencies in the main README.
- Run locust:
```
$ locust
```
- Open a browser and navigate to `http://localhost:8089`.
- Enter the number of users
- Enter host name: `http://<load_balancer_dns_name>`
- Tweak any other settings and click "Start"

# Results
You can view the results of the load testing in the `results` directory. It contains the `results/data` subdirectory with the measurements captured during my load testing: CSV files and charts exported from locust for each run of the test.

I have also created a python script `results/plot_results.py` that generates charts from the measured data.
```
$ python results/plot_results.py
```
The generated charts will be saved in the `results/plots` directory by default. They include charts comparing the response times, error rates, and requests per second of our system with RDS vs Aurora as the used database.
