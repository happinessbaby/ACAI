import bcrypt
import yaml

def hash_password(password):
    # Hash the password using bcrypt
    hashed_password = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    return hashed_password


def save_password(username, name, password, email, filename="./user_login_sample.yaml"):

    try:
        # hashed_password = hash_password(password)
        # print("hashed password", hashed_password)
        with open(filename, 'r') as file:
            credentials = yaml.safe_load(file)
            print(credentials)
            # Add the new user's details to the dictionary
        credentials['credentials']['usernames'][username] = {
            'email': email,
            'name': name,
            'password': password
        }  
        with open(filename, 'w') as file:
            yaml.dump(credentials, file)
        return True
    except Exception as e:
        return False
# Example usage


# Example usage
password = "jp901210"
filename = 'user_login_sample.yaml'
username = 'yueqi'
email = 'yueqipeng2021@gmail.com'
name = 'Yueqi Peng'
save_password(username, name, password, email)