# === Configuration ===
DOCKER_USER = your-dockerhub-username
FLASK_IMAGE = krithikv/flask-worker-app
TAG = latest

# === Docker Build & Push ===

build:
	docker build -t $(FLASK_IMAGE):$(TAG) .

push:
	docker push $(FLASK_IMAGE):$(TAG)

# === Local Dev with Docker Compose ===

up:
	docker-compose up --build -d

down:
	docker-compose down

logs:
	docker-compose logs -f

# === Kubernetes Deployments ===

# -- PROD --
deploy-prod:
	kubectl apply -f kubernetes/prod/app-prod-pvc-redis.yml
	kubectl apply -f kubernetes/prod/app-prod-deployment-redis.yml
	kubectl apply -f kubernetes/prod/app-prod-deployment-flask.yml
	kubectl apply -f kubernetes/prod/app-prod-deployment-worker.yml
	kubectl apply -f kubernetes/prod/app-prod-service-redis.yml
	kubectl apply -f kubernetes/prod/app-prod-service-flask.yml
	kubectl apply -f kubernetes/prod/app-prod-service-nodeport-flask.yml
	kubectl apply -f kubernetes/prod/app-prod-ingress-flask.yml

delete-prod:
	kubectl delete -f kubernetes/prod --ignore-not-found

# -- TEST --
deploy-test:
	kubectl apply -f kubernetes/test/app-test-pvc-redis.yml
	kubectl apply -f kubernetes/test/app-test-deployment-redis.yml
	kubectl apply -f kubernetes/test/app-test-deployment-flask.yml
	kubectl apply -f kubernetes/test/app-test-deployment-worker.yml
	kubectl apply -f kubernetes/test/app-test-service-redis.yml
	kubectl apply -f kubernetes/test/app-test-service-flask.yml
	kubectl apply -f kubernetes/test/app-test-service-nodeport-flask.yml
	kubectl apply -f kubernetes/test/app-test-ingress-flask.yml

delete-test:
	kubectl delete -f kubernetes/test --ignore-not-found

# === Testing ===

test:
	pytest test/

# === Combined Actions ===

rebuild: build push

prod: rebuild deploy-prod
testenv: rebuild deploy-test
clean: delete-prod delete-test down
