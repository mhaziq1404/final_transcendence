DC		=	docker compose -f
YAML	=	docker-compose.yml
RMRF	=	sudo rm -rf

up:
		$(DC) $(YAML) up -d

down:
		$(DC) $(YAML) down
all:
		$(DC) $(YAML) up -d --build

cclean:
		docker rm $$(docker ps -qa); \
		docker rmi -f $$(docker images -qa); \
		docker volume rm $$(docker volume ls -q); \
		docker network ls -q | grep -v -E 'bridge|host|none' | xargs -r docker network rm;

fclean:
		docker stop $$(docker ps -qa);
		docker rm $$(docker ps -qa); \
		docker rmi -f $$(docker images -qa); \
		docker volume rm $$(docker volume ls -q); \
		docker system prune; \
		docker network ls -q | grep -v -E 'bridge|host|none' | xargs -r docker network rm;

re:
		make fclean; make all

.PHONY:	all down fclean re