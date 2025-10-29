from enum import Enum

class PostgresQueries(Enum):
    GET_USER_BY_NAME_AND_PASSWORD = "get_user_by_name_and_password"

    def build_query(self, connection, **params):
        """
        Build and execute a Supabase Postgres query based on the enum type.
        :param connection: Supabase client or table connection
        :param params: query parameters (like username, password)
        :return: query result
        """
        if self == PostgresQueries.GET_USER_BY_NAME_AND_PASSWORD:
            username = params.get("username")
            password = params.get("password")
            if username is None or password is None:
                raise ValueError("Both 'username' and 'password' must be provided.")

            # Example Supabase query
            return (
                connection
                .table("user_logins")
                .select("*")
                .eq("username", username)
                .eq("hashed_password", password)
                .execute()
            )


