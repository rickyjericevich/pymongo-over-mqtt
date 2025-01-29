<!-- This readme is inspired from https://github.com/othneildrew/Best-README-Template -->

<!-- Improved compatibility of back to top link: See: https://github.com/othneildrew/Best-README-Template/pull/73 -->
<a id="readme-top"></a>

<!-- PROJECT SHIELDS -->
<!--
*** I'm using markdown "reference style" links for readability.
*** Reference links are enclosed in brackets [ ] instead of parentheses ( ).
*** See the bottom of this document for the declaration of the reference variables
*** for contributors-url, forks-url, etc. This is an optional, concise syntax you may use.
*** https://www.markdownguide.org/basic-syntax/#reference-style-links
-->
[![Contributors][contributors-shield]][contributors-url]
[![Forks][forks-shield]][forks-url]
[![Stargazers][stars-shield]][stars-url]
[![Issues][issues-shield]][issues-url]
[![Unlicensed][license-shield]][license-url]
[![LinkedIn][linkedin-shield]][linkedin-url]

<!-- PROJECT LOGO -->
<br />
<div align="center">
<!--   <a href="https://github.com/rickyjericevich/pymongo-over-mqtt">
    <img src="images/logo.png" alt="Logo" width="80" height="80">
  </a> -->

<h3 align="center">PyMongo over MQTT</h3>

  <p align="center">
    Execute PyMongo commands directly through MQTT
    <br />
    <br />
<!--     <a href="https://github.com/rickyjericevich/pymongo-over-mqtt">View Demo</a> -->
<!--     &middot; -->
    <a href="https://github.com/rickyjericevich/pymongo-over-mqtt/issues/new?labels=bug&template=bug-report---.md">Report Bug</a>
    &middot;
    <a href="https://github.com/rickyjericevich/pymongo-over-mqtt/issues/new?labels=enhancement&template=feature-request---.md">Request Feature</a>
  </p>
</div>



<!-- TABLE OF CONTENTS -->
<details>
  <summary>Table of Contents</summary>
  <ol>
    <li>
      <a href="#about-the-project">About The Project</a>
      <ul>
        <li><a href="#built-with">Built With</a></li>
      </ul>
    </li>
    <li>
      <a href="#getting-started">Getting Started</a>
      <ul>
        <li><a href="#configure-environment-variables">Configure environment variables</a></li>
        <li><a href="#build-the-docker-image">Build the Docker image</a></li>
        <li><a href="#run-the-container">Run the container</a></li>
      </ul>
    </li>
    <li>
      <a href="#usage">Usage</a>
      <ul>
        <li><a href="#topic">Topic</a></li>
        <li><a href="#payload">Payload</a></li>
        <li><a href="#response-topic">Response topic</a></li>
        <li>
          <a href="#examples">Examples</a>
          <ul>
            <li><a href="#collection.find-(python-paho-client)">Collection.find (Python Paho client)</a></li>
            <li><a href="#database.insert_one-(java-hivemq-client)">Database.insert_one (Java HiveMQ client)</a></li>
            <li><a href="#collection.list_collection_names-(nodejs-mqtt.js-client)">Collection.list_collection_names (NodeJS MQTT.js client)</a></li>
          </ul>
        </li>
      </ul>
    </li>
    <li><a href="#roadmap">Roadmap</a></li>
    <li>
      <a href="#contributing">Contributing</a>
      <ul>
        <li><a href="#top-contributors">Top contributors</a></li>
      </ul>
    </li>
<!--     <li><a href="#license">License</a></li> -->
    <li><a href="#contact">Contact</a></li>
  </ol>
</details>


<!-- ABOUT THE PROJECT -->
## About The Project

<!-- [![Product Name Screen Shot][product-screenshot]](https://example.com) -->

This project enables any MQTT client to run [PyMongo](https://pymongo.readthedocs.io/en/stable/#) commands and receive the output of thereof.

It satisfies a need for edge devices that already leverage MQTT connections, such as [AMRs](https://www.intel.com/content/www/us/en/robotics/autonomous-mobile-robots/overview.html) or mobile devices, to perform almost any PyMongo operation on a MongoDB database.

Once deployed on your backend, your MQTT clients can interact with your MongoDB database through this client without you having to build your own backend API or pay for a [MongoDB Atlas](https://www.mongodb.com/products/platform/atlas-database) subscription.

<p align="right"><a href="#readme-top">Back to top</a></p>


### Built With

[![Motor][Motor]][Motor-url]

[![gmqtt][gmqtt]][gmqtt-url]

[![Pydantic][Pydantic.dev]][Pydantic-url]


<p align="right"><a href="#readme-top">Back to top</a></p>



<!-- GETTING STARTED -->
## Getting Started

The instructions below are to run the app as a Docker container. If you want to run it locally, see the [Dockerfile](Dockerfile) for the setup steps.

### Configure environment variables

Populate a .env file with the required variables. You can use [.env.example](.env.example) as a template.

`LOG_LEVEL`: One of the [logging module's log levels](https://docs.python.org/3/library/logging.html#logging-levels) (default=INFO).

`BROKER_HOST`: The URL to your MQTT broker that this client will connect to (default=localhost).

`MQTT_PORT`: The port to connect to your MQTT broker (default=1883).

`MONGODB_URI`: The URL to your MongoDB instance (default=mongodb://localhost:27017).

`BASE_TOPIC`: The topic to which this client subscribes in order to process messages published by other clients (default=mongodb). See [Usage](#usage) for more detail.

### Build the Docker image
```
docker build -t pymongo_over_mqtt_img .
```

### Run the container
```
docker run --name pymongo_over_mqtt --env-file .env pymongo_over_mqtt_img
```


<p align="right"><a href="#readme-top">Back to top</a></p>



<!-- USAGE EXAMPLES -->
## Usage

At startup, this client subscribes to the wildcard topic `BASE_TOPIC/#`. When another client publishes to a topic like `BASE_TOPIC/<something>/<something else>/...`, this client will receive the message and attempt to process it.

For this client to correctly process messages, other clients should structure their messages as follows:

### Topic

The topic string must be of the form:

1. `BASE_TOPIC/<database_name>/<pymongo_function_name>`
2. `BASE_TOPIC/<database_name>/<collection_name>/<pymongo_function_name>`

Option 1 runs the specified function on the specified database while option 2 runs the specified function on the specified collection. Here's the list of available database and collection functions (not all are supported):
1. [Database functions](https://pymongo.readthedocs.io/en/stable/api/pymongo/database.html)
2. [Collection functions](https://pymongo.readthedocs.io/en/stable/api/pymongo/collection.html)


### Payload

The payload must be a stringified [JSON object literal](https://developer.mozilla.org/en-US/docs/Learn_web_development/Core/Scripting/JSON#json_structure) in MongoDB's [Exended JSON](https://www.mongodb.com/docs/manual/reference/mongodb-extended-json/) format.

The JSON object's key-value pairs must be a subset of the PyMongo function's keyword arguments. For example, to run PyMongo's [find_one](https://pymongo.readthedocs.io/en/stable/api/pymongo/collection.html#pymongo.collection.Collection.find_one) command,  the topic would be similar to `mongodb/prod/users/find_one`, and the payload similar to `{"filter": {"name": "John"}, "skip": 5}`

Note that some function parameters that have more complex data types are not supported, such as `session`, whose data type is [ClientSession](https://pymongo.readthedocs.io/en/stable/api/pymongo/client_session.html#pymongo.client_session.ClientSession).


### Response topic

Another client can define one or more response topics, and the return value of the PyMongo function, if not `None`, will be published to it.

Response topics should not begin with `BASE_TOPIC` for obvious reasons.

### Examples

Below are some code snippets that briefly demonstrates how other clients would make requests and receive responses. Full examples can be found in the [examples folder](examples)

#### Collection.find (Python [Paho](https://pypi.org/project/paho-mqtt/) client)
Add a callback to receive messages from the subscribed topic
```python
def on_message(client, userdata, msg):
    response = json_util.loads(msg.payload.decode()) # rehydrate bson objects like objectId

...

mqtt_client.on_message = on_message
```

Subscribe to the response topic
```python
client.subscribe("response/topic")
```
Then publish a message to the PyMongo topic to receive the command's output
```python
def on_subscribe(client, userdata, mid, reason_code_list, properties):
    topic = "mongodb/test_db/test_collection/find"
    payload = json_util.dumps({"filter": {}, "skip": 1, "limit": 1}) # convert dictionary to valid mongo json string
    properties = Properties(PacketTypes.PUBLISH)
    properties.ResponseTopic = "response/topic"
    client.publish(topic=, payload=, properties=)
```

#### Database.insert_one (Java [HiveMQ](https://github.com/hivemq/hivemq-mqtt-client) client)
Add a callback to receive messages from the subscribed topic
```java
public void onMessage(Mqtt5Publish mqtt5Publish) {
    Document response = Document.parse(new String(mqtt5Publish.getPayloadAsBytes())); // rehydrate bson objects like objectId
}
```
Subscribe to the response topic
```java
public void onConnect(MqttClientConnectedContext context) {
    client.subscribeWith()
            .topicFilter("response/topic")
            .callback(this::onMessage)
            .send()
            .thenCompose(this::onSubscribe);
    }
```
Then publish a message to the PyMongo topic to receive the command's output
```java
public CompletionStage<Mqtt5SubAck> onSubscribe(Mqtt5SubAck subAck) {
    MqttTopic topic = MqttTopic("mongodb/test_db/test_collection/insert_one");
    String payload = new Document("document", new Document("_id", new ObjectId())).toJson(); // convert object to valid mongo json string
    client.publishWith()
            .topic(topic)
            .payload(payload.getBytes())
            .responseTopic("response/topic")
            .send();

    return null;
}
```

#### Collection.list_collection_names (NodeJS [MQTT.js](https://github.com/mqttjs/MQTT.js) client)
Add a callback to receive messages from the subscribed topic
```javascript
function onMessage(topic, message) {
    const response = EJSON.parse(message); // rehydrate bson objects like objectId
}

...

client.on("message", onMessage);
```
Subscribe to the response topic
```javascript
client.subscribe("response/topic", onSubscribe);
```
Then publish a message to the PyMongo topic to receive the command's output
```javascript
function onSubscribe() {
    const topic = "mongodb/test_db/list_collection_names";
    const payload = EJSON.stringify({}); // convert object to valid mongo json string
    const properties = { responseTopic: "response/topic" };
    client.publish(topic, payload, { properties });
}
```

<p align="right"><a href="#readme-top">Back to top</a></p>

<!-- ROADMAP -->

## Roadmap

- [ ] Support a broker's auth options
- [ ] Document code
- [ ] Improve handling of PyMongo command return types
- [ ] Tests

<!-- CONTRIBUTING -->
## Contributing

Contributions are what make the open source community such an amazing place to learn, inspire, and create. Any contributions you make are **greatly appreciated**.

If you have a suggestion that would make this better, please fork the repo and create a pull request. You can also simply open an issue with the tag "enhancement".
Don't forget to give the project a star! Thanks again!

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

<p align="right"><a href="#readme-top">Back to top</a></p>

### Top contributors

<a href="https://github.com/rickyjericevich/pymongo-over-mqtt/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=rickyjericevich/pymongo-over-mqtt" alt="contrib.rocks image" />
</a>



<p align="right"><a href="#readme-top">Back to top</a></p>



<!-- CONTACT -->
## Contact

Ricky Jericevich - [linkedin.com/in/rickyjericevich](http://www.linkedin.com/in/rickyjericevich) - rickyjericevich@gmail.com

Project Link: [pymongo-over-mqtt](https://github.com/rickyjericevich/pymongo-over-mqtt)

<p align="right"><a href="#readme-top">Back to top</a></p>



<!-- MARKDOWN LINKS & IMAGES -->
<!-- https://www.markdownguide.org/basic-syntax/#reference-style-links -->
[contributors-shield]: https://img.shields.io/github/contributors/rickyjericevich/pymongo-over-mqtt.svg?style=for-the-badge
[contributors-url]: https://github.com/rickyjericevich/pymongo-over-mqtt/graphs/contributors
[forks-shield]: https://img.shields.io/github/forks/rickyjericevich/pymongo-over-mqtt.svg?style=for-the-badge
[forks-url]: https://github.com/rickyjericevich/pymongo-over-mqtt/network/members
[stars-shield]: https://img.shields.io/github/stars/rickyjericevich/pymongo-over-mqtt.svg?style=for-the-badge
[stars-url]: https://github.com/rickyjericevich/pymongo-over-mqtt/stargazers
[issues-shield]: https://img.shields.io/github/issues/rickyjericevich/pymongo-over-mqtt.svg?style=for-the-badge
[issues-url]: https://github.com/rickyjericevich/pymongo-over-mqtt/issues
[license-shield]: https://img.shields.io/github/license/rickyjericevich/pymongo-over-mqtt.svg?style=for-the-badge
[license-url]: https://github.com/rickyjericevich/pymongo-over-mqtt/blob/master/LICENSE.txt
[linkedin-shield]: https://img.shields.io/badge/-LinkedIn-black.svg?style=for-the-badge&logo=linkedin&colorB=555
[linkedin-url]: https://linkedin.com/in/rickyjericevich
[product-screenshot]: images/screenshot.png
[python.org]: https://img.shields.io/badge/python-000000?style=for-the-badge&logo=python
[Python-url]: https://www.python.org/
[Motor]: https://img.shields.io/badge/Motor-000000?style=for-the-badge&logo=mongodb
[Motor-url]: https://motor.readthedocs.io/
[gmqtt]: https://img.shields.io/badge/gmqtt-000000?style=for-the-badge&logo=mqtt
[gmqtt-url]: https://github.com/wialon/gmqtt
[Pydantic.dev]: https://img.shields.io/badge/Pydantic-000000?style=for-the-badge&logo=pydantic
[Pydantic-url]: https://pydantic.dev/