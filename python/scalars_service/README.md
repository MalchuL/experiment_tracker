# Copy .env.example to .env and fill the values.
`cp .env.example .env`

# Run ClickHouse
`docker run --name clickhouse-server --ulimit nofile=262144:262144 -p 8123:8123 -e CLICKHOUSE_USER=default -e CLICKHOUSE_PASSWORD=yourpass -e CLICKHOUSE_DB=metrics clickhouse/clickhouse-server`
Serve URL will be `http://default:yourpass@localhost:8123/default`. Use it as CLICKHOUSE_URL in .env file.

# Run Clickhouse UI (Optional for development purposes)
1. `docker run --name clickhouse-web-client -p 5005:80 --link clickhouse-server:clickhouse-server spoonest/clickhouse-web-client`
2. If you got an error like `is already in use by container "40ec1ea5d16b383760911b62a0a9009804dd98b2d5da9255cbac05e7e5902e03"` delete the container with `docker rm -f 40ec1ea5d16b383760911b62a0a9009804dd98b2d5da9255cbac05e7e5902e03` and run the command again.
3. Open `http://localhost:5005` in your browser. 
4. Paste your credentials and click on "Login".
Name: `default`
host:port: `localhost:8123`
login: `default`
password: `yourpass`

# Run select or other options.
By default it uses global database.
When you write a query, use `default` database.
Example: `select * from default.scalars_string`


# Run Scalars Service
`uv run uvicorn api.main:app --reload --port 8001 --log-level debug`