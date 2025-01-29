import com.hivemq.client.mqtt.MqttClient;
import com.hivemq.client.mqtt.datatypes.MqttTopic;
import com.hivemq.client.mqtt.lifecycle.MqttClientConnectedContext;
import com.hivemq.client.mqtt.mqtt5.Mqtt5AsyncClient;
import com.hivemq.client.mqtt.mqtt5.message.publish.Mqtt5Publish;
import com.hivemq.client.mqtt.mqtt5.message.subscribe.suback.Mqtt5SubAck;
import java.util.concurrent.CompletionStage;
import java.util.concurrent.TimeUnit;
import org.bson.Document;
import org.bson.types.ObjectId;

public class Main {

    private static final String BROKER = "localhost";
    private static final int PORT = 1883;
    private static final String BASE_TOPIC = "mongodb";
    private static final String DB_NAME = "test_db";
    private static final String COLLECTION_NAME = "test_collection";
    private static final String PYMONGO_COMMAND = "insert_one";
    private static final Document MESSAGE = new Document("document", new Document("_id", new ObjectId("_id of document in test_collection"))); // arguments for insert_one command
    private static final String RESPONSE_TOPIC = "test/response"; // topic that receives the output of the PyMongo command
    private static final String CLIENT_ID = "hivemq_java_client";
    private static final int TIMEOUT = 5; // seconds

    private Mqtt5AsyncClient client;
    private Thread timerThread;

    public static void main(String[] args) {
        new Main();
    }

    public Main() {
        System.out.println("Connecting to broker " + BROKER + ":" + PORT + "...");

        client = MqttClient.builder()
                .useMqttVersion5()
                .serverHost(BROKER)
                .serverPort(PORT)
                .identifier(CLIENT_ID)
                .addConnectedListener(this::onConnect)
                .buildAsync();

        client.connect();

        timerThread = Thread.currentThread();
        try {
            TimeUnit.SECONDS.sleep(TIMEOUT);
            System.out.println("No message received from response topic after " + TIMEOUT + "s. Program terminating.");
        } catch (InterruptedException e) {}

        client.disconnect().join();
    }

    public void onConnect(MqttClientConnectedContext context) {
        System.out.println("Connected to broker");
        client.subscribeWith()
                .topicFilter(RESPONSE_TOPIC)
                .callback(this::onMessage)
                .send()
                .thenCompose(this::onSubscribe);
    }

    public CompletionStage<Mqtt5SubAck> onSubscribe(Mqtt5SubAck subAck) {
        System.out.println("Subscribed to response topic: " + RESPONSE_TOPIC);

        MqttTopic topic = MqttTopic.builder()
                .addLevel(BASE_TOPIC)
                .addLevel(DB_NAME)
                .addLevel(COLLECTION_NAME)
                .addLevel(PYMONGO_COMMAND)
                .build();

        String payload = MESSAGE.toJson(); // convert object to valid mongo json string

        System.out.println("Publishing message to topic: " + topic + ", payload: " + payload);
        client.publishWith()
                .topic(topic)
                .payload(payload.getBytes())
                .responseTopic(RESPONSE_TOPIC) // include the response topic in the message properties
                .send();

        return null;
    }

    public void onMessage(Mqtt5Publish mqtt5Publish) {
        Document response = Document.parse(new String(mqtt5Publish.getPayloadAsBytes())); // rehydrate bson objects like objectId
        System.out.println("Received message from response topic: " + response);
        timerThread.interrupt();
    }

}
