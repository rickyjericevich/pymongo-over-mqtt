import { connect } from "mqtt";
import { EJSON } from "bson";


const BROKER = "localhost";
const PORT = 1883;
const BASE_TOPIC = "mongodb";
const DB_NAME = "test_db";
const PYMONGO_COMMAND = "list_collection_names";
const MESSAGE = {}; // empty because the list_collection_names command takes no arguments
const RESPONSE_TOPIC = "test/response"; // topic that receives the output of the PyMongo command
const CLIENT_ID = "mqttjs_nodejs_client";
const TIMEOUT = 5000; // milliseconds


function onConnect() {
    console.log("Connected to broker");
    client.subscribe(RESPONSE_TOPIC, onSubscribe);
}

function onSubscribe() {
    console.log(`Subscribed to response topic: ${RESPONSE_TOPIC}`);

    const topic = `${BASE_TOPIC}/${DB_NAME}/${PYMONGO_COMMAND}`;
    const payload = EJSON.stringify(MESSAGE); // convert object to valid mongo json string
    const properties = { responseTopic: RESPONSE_TOPIC }; // include the response topic in the message properties

    console.log(`Publishing message to topic: ${topic}`);
    client.publish(topic, payload, { properties });
}

function onMessage(topic, message) {
    const response = EJSON.parse(message); // rehydrate bson objects like objectId
    console.log("Received message from response topic:", response);
    clearTimeout(timer);
    client.end();
}

console.log(`Connecting to broker ${BROKER}:${PORT}...`)

const client = connect(`mqtt://${BROKER}:${PORT}`, { clientId: CLIENT_ID, protocolVersion: 5 });
client.on("connect", onConnect);
client.on("message", onMessage);
client.on("error", console.error);

const timer = setTimeout(() => {
    console.log(`No message received from ${RESPONSE_TOPIC} within ${TIMEOUT / 1000}s. Program terminating.`);
    client.end();
}, TIMEOUT);
