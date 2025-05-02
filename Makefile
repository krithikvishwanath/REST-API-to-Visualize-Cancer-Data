DOCKER_USER = krithikv   
FLASK_IMAGE = $(DOCKER_USER)/flask-worker-app
TAG         = latest

build:      ; docker build -t $(FLASK_IMAGE):$(TAG) .
push:       ; docker push $(FLASK_IMAGE):$(TAG)

up:         ; docker-compose up --build -d
down:       ; docker-compose down
logs:       ; docker-compose logs -f

deploy-prod: ; kubectl apply -f kubernetes/prod
delete-prod: ; kubectl delete -f kubernetes/prod --ignore-not-found
deploy-test: ; kubectl apply -f kubernetes/test
delete-test: ; kubectl delete -f kubernetes/test --ignore-not-found

test:       ; pytest -q
rebuild:    ; $(MAKE) build push
