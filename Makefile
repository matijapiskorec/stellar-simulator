
container="stellar"

build: docker-compose.yaml
	docker-compose up -d --force-recreate && docker-compose exec $(container) pip install -r requirements.txt

start: docker-compose.yaml
	docker-compose up -d 

bash: docker-compose.yaml
	docker-compose exec $(container) bash

ls:
	docker container ls

kill:
	docker kill $(container)

simulator:
	python3 src/Simulator.py -v 5 -n 2

simulator-file:
	python3 src/Simulator.py > output/$$(date +"%Y%m%d").txt 2>&1

test:
	python3 src/Test.py

test-single:
	python3 src/Test.py SimulatorTest.test_initialize_simulator

todo:
	grep --color=always -nr "TODO" ./src | sed 's/ \+/ /g'

