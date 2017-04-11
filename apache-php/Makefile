NAME = shengliang/apache-php
VERSION = 0.0.1

.PHONY : all clean build

all: build tag_latest

build:
	docker build -t $(NAME):$(VERSION) .

tag_latest:
	docker tag $(NAME):$(VERSION) $(NAME):latest

clean:
