1. Opis zadania
Zadanie polega na stworzeniu mikroserwisu wspierającego pracę programistów zajmujących się
uczeniem maszynowym. System ma pomóc w gromadzeniu i udostępnianiu informacji pobranych z
sieci. Główną funkcjonalnością systemu jest pobieranie tekstu oraz obrazków ze stron
internetowych.
2. Funkcjonalność
• Zlecenie pobrania tekstu z danej strony internetowej i zapis jej w systemie.
• Zlecenie pobrania wszystkich obrazków z danej strony i zapis ich w systemie.
• Sprawdzenie statusu zleconego zadania.
• Możliwość pobrania stworzonych zasobów (tekstu i obrazków).
3. Architektura
• Zadanie polega na zaprojektowaniu i zaimplementowaniu REST API dla tego systemu.
• Mikroserwis powinien być napisany w języku Python.
• Rozwiązanie powinno zawierać testy automatyczne.
• Uruchomienie mikroserwisu powinno być maksymalnie zautomatyzowane (preferowane użycie
Dockera lub podobnych narzędzi).
4. FAQ
• Czy wymagane jest wykonanie Javascriptu w celu uzyskania tekstu/obrazków na stronie? Nie,
pobieramy tylko statyczne zasoby.
• Czy z tekstu pobieranego ze stron powinien usuwać tagi HTML i kod Javascript? Tak.
• Czy napisanie frontendu jest częścią zadania? Nie.
• Czy można założyć, że pobieranie tekstu/obrazków ze strony jest szybkie? Nie, pobieranie może
trwać bardzo długo.
• Pisząc o stronie internetowej mamy na myśli pojedynczy dokument HTML /konkretny URL (i obrazki
w nim zalinkowane).

# recruitment task

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
- /images_tasks  *POST, GET*
- /images_tasks/id  *GET*
- /images_tasks/id/images *GET*
- /images_tasks/id/images/id  *GET*
- /text_tasks POST, *GET*
- /text_tasks/id *GET*
- /text_tasks/id/text *GET*


## Info
The whole microservice consists of 5 *containers*:
- *Flask* REST application
- *Celery* task application
- *Mongodb*
- *Nginx*
- *Rabbitmq*

specified as *docker-compose services*. To scale it, add more celery workers.

Request to collect data is received by REST API application. It stores the task and dispatches async task to *celery* over *rabbitmq*.
The *celery* tasks use *asyncio* to gather data in order to speed up performance. It also manages task data/status and does 
updates in *mongodb* appropiately. 
Images are downloaded to shared volume, which is attached to *Nginx*. *Nginx* serves them later as staticfiles.

Storage mechanism prevents from saving duplicates (i.e. images from same src url).
If a task (website) has an image, which is already stored, download will be skipped - nevertheless, image will be availabe as a resource of the current task. 

Race condition on image saving are very unlikely to happen. 
If they do, exception is properly handled to set the failed task to 'success' and link it to the image of the other task.

If a task can see, that its resource collection has been attempted in the past:
 - it skips it, if it was successful
 - tries again, if it was error
 - its skips it, if it is being in progress by other task
 
 ## About realisation
 I chose *Flask*, *Celery* and *Mongodb*, even though I have never used them before:
 - *Flask*, as a microframework, seemed to be ok for such as small rest api application
 - *Celery* helped to perform task asynchronously and will be good for scaling
 - never used *Mongodb*, so wanted to have some fun
 - *Flask* and *Mongodb* caused me a lot of troubles:
   - spent a lot of time on choosing libraries (i.e. had to revert solution from *pymongo* to *mongoengine* with *ORM*)
   - first time configuration is never straightforward
   
 ## Most interesting points (python skill indicators)
 - quite nice api *Resource* class inheritance structure (**app/api/endpoints/***)
 - *asyncio* usage (**app/models.py**, **app/utils.run_with_asyncio**)
 - selective mocking of client session, session context using **set_side_effect** fixture (**app/tests/conftest.py**, **app/tests/test_tasks.py**)
 - good exception handling (**app/models.py**)
 - even **reduce** had a chance to be applied (**app/tests/conftest.py**)
   
 ## Issues:
  - There could be separate images for celery and flask. I build one, because it was easier to handle dependencies between them:
    - celery tasks and flask app both use same models
  - task coroutines were actually implemented in models. It made my life easier, but that code logically fits celery tasks better
  - celery worker may leave db connection open (to be investigated)
  - I didn't use pylint - the code should be quite PEP8-ish though 
  - there are unit tests, but for simple scenarios. It would be good to have scenarios with paraller requests, same data sources etc.
  - It would be good to have integration test, working on resources served internally by the app
  
  P.S. I hope you like my solution.
  Regards,
  Marek
 
 


