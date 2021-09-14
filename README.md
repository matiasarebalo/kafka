# Red social con Apache Kafka

ZooKeeper es un servicio centralizado para mantener la información de configuración, nombrar, proporcionar sincronización distribuida y proporcionar servicios grupales.

Para levantarlo, simplemente dirigirse a la carpeta donde se tenga instalado Apache Kafka y correr el siguiente comando:
```
.\bin\windows\zookeeper-server-start.bat .\config\zookeeper.properties
```

Para levantar el servidor Kafka:
```
.\bin\windows\kafka-server-start.bat .\config\server.properties
```

Crear un topic (por defecto son en el puerto 2181):
```
.\bin\windows\kafka-topics.bat --create --zookeeper localhost:2181 --replication-factor 1 --partitions 1 --topic "nombreDelTopic"
```

Para ver los topics creados en un determinado puerto:
```
.\bin\windows\kafka-topics.bat --list --zookeeper localhost:2181
```
