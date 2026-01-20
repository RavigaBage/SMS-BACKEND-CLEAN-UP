#!/bin/bash
set -e

host="$DB_HOST"
port="$DB_PORT"
user="$DB_USER"
password="$DB_PASSWORD"

until mysql -h"$host" -P"$port" -u"$user" -p"$password" -e "SELECT 1" &> /dev/null
do
  echo "MySQL is unavailable - sleeping"
  sleep 2
done

echo "MySQL is up - continuing"