FROM public.ecr.aws/docker/library/python:3.11

WORKDIR /nuxeo-component-ordering

COPY --chmod=744 scripts/ .
COPY requirements.txt .

RUN pip3 install -r requirements.txt