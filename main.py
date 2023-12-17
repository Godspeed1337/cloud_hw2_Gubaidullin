import os
import boto3
import argparse
import json


CONFIG_FILE = "config.json"

storage_client = None

def get_storage_client(aws_access_key_id, aws_secret_access_key):
    global storage_client
    if storage_client is not None:
        return storage_client

    storage_client = boto3.client('s3',
                                  aws_access_key_id=aws_access_key_id,
                                  aws_secret_access_key=aws_secret_access_key,
                                  endpoint_url='https://storage.yandexcloud.net',
                                  region_name='ru-central1')
    return storage_client



def init():
    aws_access_key_id = input("Enter AWS Access Key ID: ")
    aws_secret_access_key = input("Enter AWS Secret Access Key: ")
    bucket_name = input("Enter bucket name: ")

    # Инициализация boto3 и создание бакета
    s3 = get_storage_client('s3', aws_access_key_id=aws_access_key_id, aws_secret_access_key=aws_secret_access_key,
                      endpoint_url='https://storage.yandexcloud.net', region_name='ru-central1')
    try:
        s3.create_bucket(Bucket=bucket_name)
    except Exception as e:
        print(e)

    # Сохранение настроек в файл конфигурации
    config = {
        "aws_access_key_id": aws_access_key_id,
        "aws_secret_access_key": aws_secret_access_key,
        "bucket": bucket_name
    }
    with open(CONFIG_FILE, "w") as config_file:
        json.dump(config, config_file)


def upload_photos(album, path=".", **kwargs):
    print(album)
    print(path)


def download_photos(album, photos_dir=".", **kwargs):
    # Загрузка фотографий из облачного хранилища
    # (используйте boto3 для загрузки фотографий из вашего бакета)
    pass


def list_albums(album=None, **kwargs):
    # Просмотр списка альбомов и фотографий в альбоме
    # (используйте boto3 для получения списка объектов в вашем бакете)
    pass


def delete(album, photo=None, **kwargs):
    # Удаление альбомов и фотографий
    # (используйте boto3 для удаления объектов из вашего бакета)
    pass


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Manage cloud photo storage.")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Инициализация
    init_parser = subparsers.add_parser("init", help="Initialize the program")
    init_parser.set_defaults(func=init)

    # Загрузка фотографий
    upload_parser = subparsers.add_parser("upload", help="Upload photos to an album")
    upload_parser.add_argument("--album", required=True, help="Album name")
    upload_parser.add_argument("--path", default=".", help="Directory containing photos")
    upload_parser.set_defaults(func=upload_photos)

    # Загрузка фотографий
    download_parser = subparsers.add_parser("download", help="Download photos from an album")
    download_parser.add_argument("--album", required=True, help="Album name")
    download_parser.add_argument("--path", default=".", help="Directory to save photos")
    download_parser.set_defaults(func=download_photos)

    # Просмотр списка альбомов и фотографий
    list_parser = subparsers.add_parser("list", help="List albums or photos in an album")
    list_parser.add_argument("--album", help="Album name")
    list_parser.set_defaults(func=list_albums)

    # Удаление альбомов и фотографий
    delete_parser = subparsers.add_parser("delete", help="Delete albums or photos")
    delete_parser.add_argument("--album", required=True, help="Album name")
    delete_parser.add_argument("--photo", help="Photo name")
    delete_parser.set_defaults(func=delete)

    args = parser.parse_args()

    if args.command == "init":
        args.func()
    else:
        # Проверка наличия конфигурационного файла
        if not os.path.exists(CONFIG_FILE):
            print("Error: Configuration file not found. Run 'init' command first.")
            exit(1)

        # Загрузка конфигурации
        with open(CONFIG_FILE, "r") as config_file:
            config = json.load(config_file)
        get_storage_client()
        # Выполнение соответствующей команды
        args.func(**vars(args), **config)
