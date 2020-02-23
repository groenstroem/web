#!/bin/sh
uwsgi --http 0.0.0.0:3031 -w wsgi --callable app --processes 4 --threads 2
