import os 

def install_requirements():
    os.system('pip install -r requirements.txt')
    print("All required packages have been installed.")

if __name__ == "__main__":
    install_requirements()