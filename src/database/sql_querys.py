from enum import Enum


class SQLQueries(Enum):
    GET_USER_BY_NAME_and_PASSWORD = "SELECT * FROM user_logins WHERE username=%s AND password=%s"
    GET_ID_OF_USER = "SELECT id FROM user_logins WHERE username=%s"
    GET_HISTORY_OF_USER_ID = "SELECT * FROM tours WHERE user_id=%s ORDER BY created_at DESC"

    GET_CHILDREN_INSTANCE = """
        SELECT surname, forname, street, housenumber, postcode 
        FROM children
        WHERE surname IN ({surnames})
        AND postcode IN ({plzs})
    """



    INSERT_NEW_TOUR = """
        INSERT INTO tours (titelname, user_id, total_distance_malt, total_distance_maps, created_at)
        VALUES (%s, %s, %s, %s, NOW())
    """

    INSERT_NEW_SINGLE_TOUR = """
        INSERT INTO single_tour (tour_id, tour_symbol, tour_number, total_distance_malt, total_distance_maps) 
        VALUES (%s, %s, %s, %s, %s)
    """
    INSERT_NEW_CHILDREN = """
        INSERT INTO children (surname, forname, street, housenumber, postcode, region) 
        VALUES (%s, %s, %s, %s, %s, %s)
    """

    INSERT_NEW_TOUR_ASSIGNMENT = """
        INSERT INTO tour_assignments (tour_id, children_id, stop_order) 
        VALUES (%s, %s, %s)
    """

    def get_query(self):
        return self.value

    def format_query(self, **kwargs):
        return self.value.format(**kwargs)
