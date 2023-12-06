# treexpert

Expert System Decision API developed with django and django-ninja

**Key Features**:

- **save** different kinds of binary decision trees with versioning and
  explanations for each step (also see treeditor)
- **run** one of your saved trees for an entity with the given information
- **receive** the detailed path taken through the tree with the provided
  information
- **explain** this path with the information embedded into your decision tree

**Maintainer**: [Paula Kammler](mailto:paula@kammler.co)

## Prerequisites

- Python 3 according to [Django](https://djangoproject.com) requirements (tested with version 3.8.10s) including pip and virtualenv
- [PostgreSQL](https://www.postgresql.org/) (tested with version 14.8)
- [virtualenv](https://virtualenv.pypa.io/en/latest/index.html)

## How to install and start the API

1. clone this repo
2. move into the root of the project: `cd treexpert` (in this folder the
   `manage.py` should be found)
3. create a virtual environment: `python3 -m venv env`
4. start the virtual environment: `source env/bin/activate` (Windows:
   `source env/Scripts/activate`)
5. install requirements: `pip install -r requirements.txt`
6. migrate database: `python manage.py migrate`
7. start development server: `python manage.py runserver`

After development deactivate the virtual environment with: `deactivate`

Start the app again? -> repeat steps 4 and 7

## Usage

With the standard settings used above, the API can be explored at
[http://127.0.0.1:8000/api/docs](http://127.0.0.1:8000/api/docs).
See **Your first tree** below for a detailed explanation about the different
components of the software.

## Development

### Linter

This project uses the [black](https://black.readthedocs.io/en/stable) formatter
which will be installed with the requirements.

### Testing

To run all tests in this project, go to the app root (the one with the
`manage.py` in it) and run `python manage.py test`.

It is also possible to generate a test coverage report like it's done in the
pipeline. To do this locally run the following commands from the project root:

- `coverage run --source='.' manage.py test`
- `coverage report`
- `coverage html`

Now you should see a folder named `htmlcov`, open the `index.html` in there in
your browser and explore the files that you would like to see the coverage for.

### Dropping all tables

Sometimes during development dropping all tables in your database is required
or useful. To do this use the commands below. Be careful not to drop something
you still need!

```SQL
DROP SCHEMA public CASCADE;
CREATE SCHEMA public;
```

Afterwards be sure to apply migrations (step 6 above) and optionally also load
data from seed (`python manage.py loaddata {/path/to/seed/file}`).

## Your first tree

The treexpert has three main components that play together to make a tree and
evaluate it. The `core` app that contains the data types that are used in the
`tree` app to build the nodes and leaves of a binary tree. The `decision` app
uses both to evaluate the tree with given information about an entity.

Before creating a new tree (either by sending a request through the OpenAPI
interface or with the `treeditor`) you need data types that are then used in
the nodes of the tree to specify what kind of data is compared to the given
information. Use the endpoint `/api/core/datatype/new` to create a new data
type for your tree. For example, if you are creating a tree that answers the
question "Is this a good YouTube video?", a data type for this tree could be
the length of the video (INT as `kind_of_data`) or if the video contains
controversial information (BOOL as `kind_of_data`). If you have a data dump
from a previous instance of this API, you can also use the `loaddata` command
from Django. More information about this, can be found [here](https://docs.djangoproject.com/en/4.2/ref/django-admin/#dumpdata)
and [here](https://docs.djangoproject.com/en/4.2/ref/django-admin/#loaddata).

With your data types ready (check using `/api/core/datatype/all`), you can now
create your tree. If this is the first tree of its kind, create a new tree kind
using the `/api/tree/kind/new`. The `id` of your tree kind you receive as a
response can now be used to feed your new tree to the API at the endpoint
`/api/tree/new/{kind_id}`. If you didn't create a new kind, find your tree kind
id using the endpoint `/api/tree/kind/all`.

Your tree needs to be a complete binary tree meaning that all nodes have
exactly two children. If you don't provide a complete tree it will be rejected
by the treexpert API.

### Tree Versioning

A tree can never be edited to make it possible to retrace the iterations of a
tree at any given point in time. This means that if you create a new tree
using an existing tree as the basis (=editing), this tree will get a new
version. This version can be a new major version (1.0 becomes 2.0) or a new
minor version (1.0 becomes 1.1).

### Running your first tree

To now use your newly created tree, head over to the `decision` app of this
software. There you can use the endpoint `/api/decision/{fullresult}` with the
information you have about your entity. Sticking with the YouTube video example
from above, a request would look like this:

```json
{
  "data": [
    {
      "data_type": 1, // referencing your first data type (length of video)
      "data_value": 150 // length of video in seconds
    }
  ],
  "identifier": "title of video",
  "sec_identifier": "url of video"
}
```

With this you will get a response looking similar to this:

```json
{
  "decision": {
    "identifier": "title of video", // as provided above
    "sec_identifier": "url of video",
    "version": "YouTube tree: 1.2",
    "is_preliminary": true,
    "description": "missing data at node: 1_1.2_N.2 for data type 2",
    "missing_data": 2,
    "node_missing_sth": "1_1.2_N.2"
  },
  "criteria": [
    {
      "id": "1_1.2_N.1",
      "input_value": 150,
      "result": true,
      "based_on": "1_1.2_N.2"
    }
  ]
}
```

Since the `is_preliminary` flag is set to true and `missing_data` and
`node_missing_sth` are set, this tells you that your tree needs more
information to correctly run. The `missing_data` value shows you the id of the
data type for which the information is missing. If you then also provide this
information for data type 2 like above, your result could look similar to this:

```json
{
  "decision": {
    "identifier": "title of video", // as provided above
    "sec_identifier": "url of video",
    "version": "YouTube tree: 1.2",
    "is_preliminary": false,
    "description": "This is an excellent video!",
    "result": true, // Overall answer to the question of your tree
    "leaf_id": "1_1.2_L.5"
  },
  "criteria": [
    {
      "id": "1_1.2_N.1",
      "input_value": 150,
      "result": true,
      "based_on": "1_1.2_N.2" // where did the result lead us to?
    },
    {
      "id": "1_1.2_N.2",
      "input_value": true,
      "result": false,
      "based_on": "" // no other node followed this, but the end leaf
    }
  ]
}
```

Now the tree reached a result at the end leaf with the id `1_1.2_L.5`. The
criteria list provides you with all the information necessary to reconstruct
the path through the decision tree. If you use `{fullresult}` set to true for
this endpoint, you will see much more of the information from the tree that has
been omitted here for clarity.
