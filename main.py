import os
import boto3
import argparse
import json
import configparser

CONFIG_FILE = "cloudphoto.ini"
INI_PARAM_TYPE_NAME = "DEFAULT"

storage_client = None


def get_storage_client(aws_access_key_id, aws_secret_access_key, endpoint_url, region_name):
    global storage_client
    if storage_client is not None:
        return storage_client

    storage_client = boto3.client(
        "s3",
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
        endpoint_url=endpoint_url,
        region_name=region_name,
    )
    return storage_client


def write_to_ini_file(aws_access_key_id, aws_secret_access_key, bucket_name, file_name: str = "cloudphoto.ini"):
    ini_config = configparser.ConfigParser()
    ini_config[INI_PARAM_TYPE_NAME] = {
        "aws_access_key_id": aws_access_key_id,
        "aws_secret_access_key": aws_secret_access_key,
        "bucket_name": bucket_name,
        "region_name": "ru-central1",
        "endpoint_url": "https://storage.yandexcloud.net",
    }
    with open(file_name, "w") as conf_file:
        ini_config.write(conf_file)


def read_ini_config(file_name: str = "cloudphoto.ini"):
    ini_config = configparser.ConfigParser()
    ini_config.read(file_name)
    configs = {
        "aws_access_key_id": ini_config.get(INI_PARAM_TYPE_NAME, "aws_access_key_id"),
        "aws_secret_access_key": ini_config.get(INI_PARAM_TYPE_NAME, "aws_secret_access_key"),
        "region_name": ini_config.get(INI_PARAM_TYPE_NAME, "region_name"),
        "endpoint_url": ini_config.get(INI_PARAM_TYPE_NAME, "endpoint_url"),
    }
    bucket_name = ini_config.get(INI_PARAM_TYPE_NAME, "bucket_name"),
    if isinstance(bucket_name, tuple):
        bucket_name = bucket_name[0]
    return configs, bucket_name


def init():
    global CONFIG_FILE

    aws_access_key_id = input("Enter AWS Access Key ID: ")
    aws_secret_access_key = input("Enter AWS Secret Access Key: ")
    bucket_name = input("Enter bucket name: ")

    # Инициализация boto3 и создание бакета
    s3 = get_storage_client(
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
        endpoint_url="https://storage.yandexcloud.net",
        region_name="ru-central1",
    )
    try:
        s3.create_bucket(Bucket=bucket_name)
    except Exception as e:
        print(e)

    # Сохранение настроек в файл конфигурации
    write_to_ini_file(
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
        bucket_name=bucket_name,
        file_name=CONFIG_FILE,
    )


def upload_photos(album, path=".", bucket_name="", **kwargs):
    file_list = [f for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))
                 and f.lower().endswith(('.jpg', '.jpeg'))]
    if len(file_list) == 0:
        print("Error: Фотографии не найдены")
        exit(1)
    for file in file_list:
        try:
            storage_client.upload_file(Bucket=bucket_name,
                                       Key=album + '/' + file,
                                       Filename=path + '/' + file)
        except Exception as e:
            print(f"File: {file}, error: {e}")
            continue


def download_photos(album, path=".", bucket_name="", **kwargs):
    response = storage_client.list_objects_v2(Bucket=bucket_name, Prefix=album)
    if 'Contents' not in response:
        print(f"Альбом '{album}' не найден в бакете '{bucket_name}'.")
        return
    for obj in response['Contents']:
        key = obj['Key']
        if key.endswith('/'):
            continue  # Пропускаем папки внутри бакета

        file_name = os.path.basename(key)
        local_path = os.path.join(path, file_name)

        try:
            storage_client.download_file(bucket_name, key, local_path)
            print(f"Файл '{file_name}' успешно скачан в '{local_path}'.")
        except Exception as e:
            print(f"Ошибка при скачивании файла '{file_name}': {e}")


def list_albums(album=None, bucket_name="", **kwargs):
    if album:
        prefix = album + '/'
    else:
        prefix = ""

    # Получаем список объектов (файлов и папок) в бакете
    response = storage_client.list_objects_v2(Bucket=bucket_name, Prefix=prefix, Delimiter='/')
    if not album:
        if 'CommonPrefixes' in response:
            print("Список альбомов:")
            for common_prefix in response['CommonPrefixes']:
                album_name = common_prefix['Prefix'][:-1]
                print(album_name)
        else:
            print("Ошибка: Отсутствуют альбомы")
            exit(1)
    elif album:
        print(f"Список файлов в альбоме '{album}':")
        if not response.get('Contents'):
            print("Ошибка: Альбом отсутствует")
            exit(1)
        file_names = []
        for obj in response['Contents']:
            key = obj['Key']
            if key.endswith('/'):
                continue  # Пропускаем папки внутри бакета

            file_name = os.path.basename(key)
            file_names.append(file_name)
        if len(file_names) == 0:
            print("Ошибка: Отсутствуют файлы")
            exit(1)
        else:
            for file in file_names:
                print(file)


def delete(album, photo=None, bucket_name: str = "", **kwargs):
    delimiter = "/"
    response = storage_client.list_objects_v2(Bucket=bucket_name, Prefix="", Delimiter=delimiter)
    album_presented = False
    if "CommonPrefixes" in response:
        for common_prefix in response["CommonPrefixes"]:
            album_name = common_prefix["Prefix"].strip().replace(delimiter, "")
            if album_name == album:
                album_presented = True
                break

    if not album_presented:
        print("Данного альбома нет")
        exit(1)

    response = storage_client.list_objects_v2(Bucket=bucket_name, Prefix=f"{album}/", Delimiter="/")
    cloud_object_keys = response.get("Contents", [])
    temp_cloud_keys = []
    for cloud_object in cloud_object_keys:
        temp_cloud_keys.append({"Key": cloud_object["Key"]})
    cloud_object_keys = temp_cloud_keys

    if photo is not None:
        try:
            storage_client.get_object(Bucket=bucket_name, Key=f"{album}{delimiter}{photo}")
        except Exception as e:
            print("Такого изображения нет в указанном альбоме")
            exit(1)

        for_deletion = [{"Key": f"{album}{delimiter}{photo}"}]
        storage_client.delete_objects(Bucket=bucket_name, Delete={"Objects": for_deletion})
        return

    if len(cloud_object_keys) == 0:
        for_deletion = [{"Key": f"{album}{delimiter}"}]
        storage_client.delete_objects(Bucket=bucket_name, Delete={"Objects": for_deletion})
        return

    for_deletion = cloud_object_keys
    storage_client.delete_objects(Bucket=bucket_name, Delete={"Objects": for_deletion})
    storage_client.delete_objects(Bucket=bucket_name, Delete={"Objects": [{"Key": f"{album}{delimiter}"}]})


def generate_index_page(album_names):
    with open("index.html", "w", encoding="utf-8") as index_file:
        index_file.write(
            """<!doctype html>
            <html lang="ru">
                <head>
                    <meta charset="utf-8">
                    <meta http-equiv="X-UA-Compatible" content="IE=edge">
                    <meta name="viewport" content="width=device-width, initial-scale=1">
                    
                    <title>Фотоархив</title>
                </head>
            <body>
                <h1>Фотоархив</h1>
                <ul>""")
        for index, key in enumerate(album_names):
            index_file.write(f"""<li><a href="album{index + 1}.html">{key} {index + 1}</a></li>""")
        index_file.write("""</ul>
            </body>""")


def generate_error_page():
    with open("error.html", "w", encoding="utf-8") as error_file:
        error_file.write(
            """<!doctype html>
            <html lang="ru">
                <head>
                    <meta charset="utf-8">
                    <meta http-equiv="X-UA-Compatible" content="IE=edge">
                    <meta name="viewport" content="width=device-width, initial-scale=1">
                    
                    <title>Фотоархив</title>
                </head>
            <body>
                <h1>Ошибка</h1>
                <p>Ошибка при доступе к фотоархиву. Вернитесь на <a href="index.html">главную страницу</a> фотоархива.</p>
            </body>
            </html>""")


def generate_album_page(album_name, index, bucket_name=""):
    response = storage_client.list_objects_v2(Bucket=bucket_name, Prefix=f"{album_name}/", Delimiter="/")
    file_names = []
    for obj in response['Contents']:
        key = obj['Key']
        if key.endswith('/'):
            continue  # Пропускаем папки внутри альбома

        file_name = os.path.basename(key)
        file_names.append(file_name)

    galleria_string = "{ width: 960px; height: 540px; background: #000 }"
    script_string = """<script>
                        (function() {
                            Galleria.run('.galleria');
                        }());
                    </script>"""
    with open(f"album{index + 1}.html", "w", encoding="utf-8") as album_file:
        album_file.write(f"""<!doctype html>
            <html>
                <head>
                    <link rel="stylesheet" type="text/css" href="https://cdnjs.cloudflare.com/ajax/libs/galleria/1.6.1/themes/classic/galleria.classic.min.css" />
                    <style>
                        .galleria{galleria_string}
                    </style>
                    <script src="https://ajax.googleapis.com/ajax/libs/jquery/3.6.0/jquery.min.js"></script>
                    <script src="https://cdnjs.cloudflare.com/ajax/libs/galleria/1.6.1/galleria.min.js"></script>
                    <script src="https://cdnjs.cloudflare.com/ajax/libs/galleria/1.6.1/themes/classic/galleria.classic.min.js"></script>
                </head>
                <body>
                    <div class="galleria">""")

        for file_name in file_names:
            album_file.write(f"""<img src="https://{bucket_name}.website.yandexcloud.net/{album_name}/{file_name}" data-title="{file_name}">""")
        # <img src="https://{bucket_name}.website.yandexcloud.net/album_name/" data-title="Имя_исходного_файла_фотографии_1">
        # <img src="URL_на_фотографию_2_в_альбоме" data-title="Имя_исходного_файла_фотографии_2">
        # <img src="..." data-title="...">
        # <img src="URL_на_фотографию_N_в_альбоме" data-title="Имя_исходного_файла_фотографии_N">
        album_file.write(f"""</div>
                    <p>Вернуться на <a href="index.html">главную страницу</a> фотоархива</p>
                    {script_string}
                </body>
            </html>""")


def mksite(bucket_name, **kwargs):
    storage_client.put_bucket_acl(
        ACL='public-read',  # Этот параметр устанавливает доступ к объектам в бакете для чтения всем
        Bucket=bucket_name
    )

    delimiter = "/"
    response = storage_client.list_objects_v2(Bucket=bucket_name, Prefix="", Delimiter=delimiter)
    album_names = []
    if "CommonPrefixes" in response:
        for common_prefix in response["CommonPrefixes"]:
            album_name = common_prefix["Prefix"].strip().replace(delimiter, "")
            album_names.append(album_name)

    generate_index_page(album_names)
    generate_error_page()
    website_configuration = {
        "ErrorDocument": {"Key": "error.html"},
        "IndexDocument": {"Suffix": "index.html"},
    }
    storage_client.upload_file(Bucket=bucket_name,
                               Key="index.html",
                               Filename="index.html")
    storage_client.upload_file(Bucket=bucket_name,
                               Key="error.html",
                               Filename="error.html")
    for i, album_name in enumerate(album_names):
        generate_album_page(album_name, i, bucket_name=bucket_name)
        storage_client.upload_file(Bucket=bucket_name,
                                   Key=f"album{i + 1}.html",
                                   Filename=f"album{i + 1}.html",)

    storage_client.put_bucket_website(Bucket=bucket_name,
                                      WebsiteConfiguration=website_configuration)
    print(f"Ссылка на сайт -- https://{bucket_name}.website.yandexcloud.net")


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

    # Загрузка фотографий
    download_parser = subparsers.add_parser("mksite", help="Download photos from an album")
    download_parser.set_defaults(func=mksite)

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
        config, main_bucket_name = read_ini_config(CONFIG_FILE)
        get_storage_client(**config)
        # Выполнение соответствующей команды
        args.func(**vars(args), **config, bucket_name=main_bucket_name)
