package io.sentrix.coap;

import java.io.IOException;

import org.eclipse.californium.core.CoapResource;
import org.eclipse.californium.core.CoapServer;
import org.eclipse.californium.core.coap.CoAP;
import org.eclipse.californium.core.config.CoapConfig;
import org.eclipse.californium.core.server.resources.CoapExchange;
import org.eclipse.californium.elements.config.UdpConfig;

public final class CoapBackendServer {

    private CoapBackendServer() {
    }

    public static void main(String[] args) throws IOException {
        CoapConfig.register();
        UdpConfig.register();

        CoapServer server = new CoapServer(5683);

        CoapResource sensors = new CoapResource("sensors");
        sensors.add(new CoapResource("temp") {
            @Override
            public void handleGET(CoapExchange exchange) {
                exchange.respond(CoAP.ResponseCode.CONTENT, "{\"sensor\":\"temp\",\"value\":24.7}");
            }

            @Override
            public void handlePUT(CoapExchange exchange) {
                String payload = exchange.getRequestText();
                exchange.respond(CoAP.ResponseCode.CHANGED, "updated:" + payload);
            }
        });

        CoapResource actuators = new CoapResource("actuators");
        actuators.add(new CoapResource("valve") {
            @Override
            public void handlePOST(CoapExchange exchange) {
                String payload = exchange.getRequestText();
                exchange.respond(CoAP.ResponseCode.CHANGED, "valve:" + payload);
            }
        });

        CoapResource health = new CoapResource("health") {
            @Override
            public void handleGET(CoapExchange exchange) {
                exchange.respond(CoAP.ResponseCode.CONTENT, "ok");
            }
        };

        server.add(sensors);
        server.add(actuators);
        server.add(health);

        server.start();
        System.out.println("[californium-backend] listening on udp://0.0.0.0:5683");

        Runtime.getRuntime().addShutdownHook(new Thread(server::stop));
    }
}
