# Seeding the DB

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

