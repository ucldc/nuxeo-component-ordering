FROM public.ecr.aws/docker/library/python:3.9.19

WORKDIR /nuxeo-component-ordering

COPY --chmod=744 *.py .
COPY requirements.txt .

RUN pip3 install -r requirements.txt