# semantive recruitment task

## Requirements:
- docker and docker-compose
- linux machine

## Usage:
```
./test.sh  #  run unit tests
```
```
./deploy.sh  #  deploy the service
```
```
./fetch_some_data.sh  #  trigger data collection
```

## API
/images_tasks  POST, GET
/images_tasks/id  GET
/images_tasks/id/images GET
/images_tasks/id/images/id  GET
/text_tasks POST, GET
/text_tasks/id GET
/text_tasks/id/text GET


## Info
The whole microservice consists of 5 containers:
- flask rest application
- celery task application
- mongodb
- nginx
- rabbitmq
specified as docker-compose services. To scale it, add more celery workers.

Request to collect data is received by REST API application. It stores the task and dispatches async task to celery over rabbitmq.
The celery tasks use asyncio to gather data in order to speed up performance. It also manages task data/status and does 
updates in mongodb appropiately. 
Images are downloaded to shared volume, which is attached to nginx. Nginx serves them later as staticfiles.

Storage mechanism prevents from saving duplicates (i.e. images from same src url).
If a task (website) has an image, which is already stored, download will be skipped - nevertheless, image will be availabe as a resource of the current task. 

Race condition on image saving are very unlikely to happen. 
If they do, exception is properly handled to set the failed task to 'success' and link it to the image of the other task.

If a task can see, that its resource collection has been attempted in the past:
 - it skips it, if it was successful
 - tries again, if it was error
 - its skips it, if it is being in progress by other task
 
 ## About realisation
 I chose flask, celery and mongodb, even though I have never used them before:
 - flask, as a microframework, seemed to be ok for such as small rest api application
 - celery helped to perform task asynchronically and will be good for scaling
 - never used mongodb, so wanted to have some fun
 - flask and mongodb caused me a lot of troubles:
   - spent a lot of time on choosing libraries (i.e. had to revert solution from pymongo to mongoengine with ORM)
   - first time configuration is never straightforward
   
 ## Issues:
  - There could be separate images for celery and flask. I build one, because it was easier to handle dependencies between them:
    - celery tasks and flask app both use same models
  - task coroutines were actually implemented in models. It made my life easier, but that code logically fits celery tasks better
  - celery worker may leave db connection open (to be investigated)
  - I didn't use pylint - the code should be quite PEP8-tish though 
  - there are unit tests, but for simple scenarios. It would be good to have scenarios with paraller requests, same data sources etc.
  - It would be good to have integration test, working on resources served internally by the app
  
  P.S. I hope you like my solution.
  Regards,
  Marek
 
 


