package com.refinedining.domain.nutrition;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.stereotype.Service;

import java.net.URI;
import java.net.http.*;
import java.time.Duration;
import java.util.*;

/** Present only the server's approved statements. A model response supplies their IDs. */
@Service
@ConditionalOnProperty("rag.catalog")
public class NutritionExplanation {
    private final ObjectMapper json;
    private final URI local;
    private final HttpClient client = HttpClient.newBuilder().connectTimeout(Duration.ofSeconds(2)).build();

    public NutritionExplanation(ObjectMapper json,@Value("${rag.explainer:}") String endpoint) {
        this.json = json;
        local = endpoint.isBlank() ? null : URI.create(endpoint);
        if (local != null && (!"http".equals(local.getScheme()) || !"127.0.0.1".equals(local.getHost()) ||
                local.getUserInfo() != null || local.getQuery() != null || local.getFragment() != null))
            throw new IllegalArgumentException("질의응답 설명기는 로컬 주소만 허용합니다.");
    }

    String explain(ObjectNode answer) {
        var relation = answer.required("relation");
        Map<String,String> statements = new LinkedHashMap<>();
        statements.put("match",relation.required("reason").asText());
        if (relation.path("evidenceSource").path("quote").isTextual())
            statements.put("passage", relation.path("evidenceSource").path("quote").asText());
        statements.put("review",relation.required("note").asText());
        answer.put("explanationSource","approved-record");
        if (local != null) {
            try {
                var context = Map.of("foods",answer.required("foods"), "serverValues",answer.required("rows"),
                        "verdict",relation.required("verdict"), "statements",statements);
                var schema = Map.of("type","object","properties",Map.of("id",Map.of("type","string","enum",statements.keySet())),
                        "required",List.of("id"),"additionalProperties",false);
                var request = Map.of("model","refine-qwen3","temperature",0,"max_tokens",40,
                        "chat_template_kwargs",Map.of("enable_thinking",false),
                        "messages",List.of(Map.of("role","system","content","이 비교의 근거를 설명하는 가장 관련 있는 원문 문장의 id를 고르세요."),
                                Map.of("role","user","content",json.writeValueAsString(context))),
                        "response_format",Map.of("type","json_schema","json_schema",Map.of("name","explanation","strict",true,"schema",schema)));
                HttpRequest http = HttpRequest.newBuilder(local.resolve("/v1/chat/completions")).timeout(Duration.ofSeconds(12))
                        .header("Content-Type","application/json").POST(HttpRequest.BodyPublishers.ofByteArray(json.writeValueAsBytes(request))).build();
                var response = client.send(http,HttpResponse.BodyHandlers.ofByteArray());
                if (response.statusCode() == 200) {
                    JsonNode choice = json.readTree(response.body()).at("/choices/0");
                    String id = json.readTree(choice.at("/message/content").asText()).path("id").asText();
                    if ("stop".equals(choice.path("finish_reason").asText()) && statements.containsKey(id)) {
                        answer.put("explanationSource","local-model:"+id);
                        return statements.get(id);
                    }
                }
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
            } catch (java.io.IOException | RuntimeException ignored) {
                // The approved reason below is available when the optional model is offline.
            }
        }
        return statements.get("match");
    }
}
