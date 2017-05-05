FROM eboraas/apache-php

RUN apt-get update && apt-get -y install curl iputils-ping && apt-get clean && rm -rf /var/lib/apt/lists/*

EXPOSE 80
EXPOSE 443

CMD ["/usr/sbin/apache2ctl", "-D", "FOREGROUND"]
