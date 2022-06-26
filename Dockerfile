FROM python:3.9

WORKDIR /usr/src/api

COPY requirements.txt ./
RUN pip3 install --upgrade pip
RUN pip3 install mysql-connector-python
RUN pip3 install --no-cache-dir -r requirements.txt

COPY . .

CMD [ "python", "./__main__.py" ]