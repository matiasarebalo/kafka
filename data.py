from faker import Faker
import time


fake = Faker()

""" def get_registered_user():
        return{
            "name":fake.name(),
            "address":fake.address(),
            "created_at":fake.year()
        }

 """
def get_registered_user(name,post):
        return{
        "name" : name,
        "address" : post,
        "created_at" : time.clock_gettime}

if __name__=="__main__":
        ret_value = get_registered_user()
        if ret_value is not None:
            print(get_registered_user())