import logging

def validate_topic(topic: str) -> tuple[str, str, str, str | None]:

    # validate that the topic has the forms:
    # - mongo/<database>/<collection name>/<operation> or
    # - mongo/<database>/<collection name>/<operation>/<anystring>

    # database must be a valid database name. Right now the only database for a ctrl3 site is 'db'
    # collection name must be one of the predefined collections
    # operation must be one of the predefined operations: find, insert, update, delete etc
    
    

    if len(split_topic) < 4:
        logging.error(f"Topic does not have the correct number of paths: {topic}")
        return ()

    mongo_identifier, *split_topic = split_topic
    if mongo_identifier != "mongodb":
        logging.error(f"Topic does not start with 'mongodb': {topic}")
        return ()
    
    database, *split_topic = split_topic
    if not database: #database != "db": # TODO: use an enum here for the available database names
        logging.error(f"Topic does not have a valid database name: {topic}")
        return () # TODO: return an error message to the response topic
    
    collection_name, *split_topic = split_topic
    if not collection_name: # collection_name not in ["test","robots", "logistics_robot_statuses", "navigation_events", "payload_events"]: # TODO: use an enum here for the available collection names
        logging.error(f"Topic does not have a valid collection name: {topic}")
        return () # TODO: return an error message to the response topic
    
    operation, *split_topic = split_topic
    if operation not in ["find", "aggregate", "insert_one", "update_one"]:  # TODO: use an enum here for the available operations
        logging.error(f"Topic does not have a valid mongodb operation: {topic}")
        return ()
    
    remaining_topic = "/".join(split_topic)
    
    return database, collection_name, operation, remaining_topic


def validate_response_topics(response_topics: list[str]) -> list[str]:
    if response_topics is None or len(response_topics) == 0:
            return []

    logging.debug(f"reponse topic type: {type(response_topics)}")
    # iterate from the end of the list so that we can delete elements without affecting the index
    for i in range(len(response_topics)-1, -1, -1):
        rt = response_topics[i]
        logging.debug(f"reponse topic: {rt}")
        if rt is None or rt == "":
            logging.debug(f"reponse topic is empty: {rt}")
            del response_topics[i]
            logging.warn(f"Removed invalid response topic at index {i}: {rt}")
        elif rt.startswith("mongobdb/"): # if response topic starts with mongodb/, this program will enter a never ending loop as it publishes to the response topic which triggers this function again
            logging.debug(f"reponse topic starts with mongodb: {rt}")
            del response_topics[i]
            logging.error(f"Removed response topic at index {i} as it cannot start with 'mongodb/': {rt}")

    
    return response_topics