# restApiService

## Build it

```
sudo docker build -t flask-python:latest .
```


## Run it

```
sudo docker-compose up -d
```


## Access to the shell

For access to flask container:
```
docker exec -ti flask-python /bin/bash
```

For access to mysql container:
```
sudo docker exec -ti api_db_1 /bin/bash
```


## See it in action