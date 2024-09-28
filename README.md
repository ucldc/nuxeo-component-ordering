# nuxeo-component-ordering
Scripts for figuring out and fixing what's going on with Nuxeo component ordering of complex objects. We discovered a Nuxeo bug where moving documents from one parent folder/object to another caused the `hierarchy.pos` value in the database to be set to NULL. (See https://github.com/ucldc/rikolti/issues/985).

The two primary scripts cannot be run locally because the Nuxeo database is locked down in a VPC. Instead, run the scripts in Fargate in a docker container.

The CloudFormation templates in the sceptre directory are used to create the CodeBuild project and ECS task definition needed to run the container in ECS.

## Generate report of complex objects with ordering problem

The `scripts/complex_objects_no_order.py` script generates a couple of reports listing parent objects whose children have no order value in the database.

To run this script in ECS:

Create an env.local file by running `cp env.local.example env.local` and populating the values as appropriate. Then source the file by running `source env.local`.

Make sure you have your AWS credentials set in your environment for the `pad-dsc-admin` account.

Then to run the script in ECS:

```
python run_complex_objects_no_order_in_ecs.py
```

A json report and a txt report listing the parent objects that have more than one component object without an order value will be written to S3 (to the value of `OUTPUT_URI`). The logs will be written to CloudWatch. The log group is `nuxeo-component-ordering`. The script will print the ARN of the ECS task.

## Fix component objects with no order

The `scripts/fix_components_with_no_order.py` script assigns a `hierarchy.pos` value for each component in the database. It also updates ElasticSearch with the same data.

To run this script in ECS:

If you haven't already, create an env.local file by running `cp env.local.example env.local` and populating the values as appropriate. Then source the file by running `source env.local`.

Make sure you have your AWS credentials set in your environment for the `pad-dsc-admin` account.

Then to run the script in ECS:

```
python run_fix_components_with_no_order_in_ecs.py
```

A json report listing the records that have been updated will be written to S3(to the value of `OUTPUT_URI`). The logs will be written to CloudWatch. The log group is `nuxeo-component-ordering`. The script will print the ARN of the ECS task.

## Docker Development

You can use the `compose-dev.yaml` file to build the Docker image, but be aware that you won't be able to connect to the database from your local machine, so you'll only be able to get so far. But it might be useful for doing a basic check that you can build the image.

Create an env.docker file by running `cp env.docker.example env.docker` and populating the values as appropriate.

Then to build the image:

```
docker compose -f compose-dev.yaml build
```

And to run the image (with the caveat that running the scripts in a local docker container won't work because you RDS will refuse your connection):

```
docker compose -f compose-dev.yaml up
```

## Deploy Docker image to ECR

To deploy the Docker image to ECR, start a build of the `nuxeo-component-ordering` CodeBuild project. There is no webhook for triggering a build when changes are pushed to github because we probably won't ever have to run this again. We can add one if it becomes necessary.

## Update AWS Resources (CodeBuild project, ECS task definition)

You'll need to install sceptre.

Make your changes to the template(s). Then, from inside the sceptre directory:

```
sceptre launch -y component-ordering.yaml
```