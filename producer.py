from time import sleep
from app import json_serializer
from kafka import KafkaProducer
import json
import time
from data import get_registered_user


def json_serializer(data):
    return json.dumps(data).encode("utf-8")

producer = KafkaProducer(bootstrap_servers=['192.168.0.36:9092'],
                        value_serializer=json_serializer)

if __name__ == "__main__":
    while 1==1:
        registered_user = get_registered_user()
        print(registered_user)
        producer.send("registered_user", registered_user)
        time.sleep(4)