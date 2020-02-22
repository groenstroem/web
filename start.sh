uwsgi --http 127.0.0.1:3031 -w wsgi --callable app --processes 4 --threads 2
