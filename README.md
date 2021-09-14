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
