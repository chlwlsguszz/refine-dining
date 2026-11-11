package com.refinedining.domain.weight;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import java.io.IOException;
import java.net.URI;
import java.net.http.*;
import java.time.Duration;
import java.util.List;
import java.util.Map;

/** Optional local E5 suggestions. Returned names never authorize a numeric estimate. */
@Component
public class YieldNameSuggestions {
    public record RankedEvidence(String id, Double score) {}
    public record Ranking(String engine, List<RankedEvidence> matches) {}
    private final ObjectMapper json;
    private final URI endpoint;
    private final HttpClient client = HttpClient.newBuilder().connectTimeout(Duration.ofMillis(500)).build();

    public YieldNameSuggestions(ObjectMapper json, @Value("${yield.search-url:${YIELD_SEARCH_URL:}}") String url) {
        this.json = json;
        endpoint = url.isBlank() ? null : URI.create(url);
        if (endpoint != null && (!"http".equals(endpoint.getScheme()) || !"127.0.0.1".equals(endpoint.getHost())
                || endpoint.getUserInfo() != null || endpoint.getQuery() != null || endpoint.getFragment() != null))
            throw new IllegalArgumentException("중량 예측의 이름 검색기는 로컬 HTTP 주소만 사용할 수 있습니다.");
    }

    List<String> find(String name, List<String> allowed) {
        if (endpoint == null || allowed.isEmpty()) return List.of();
        try {
            byte[] data = json.writeValueAsBytes(Map.of("name",name,"labels",allowed));
            var request = HttpRequest.newBuilder(endpoint.resolve("/suggest")).timeout(Duration.ofSeconds(2))
                    .header("Content-Type","application/json").POST(HttpRequest.BodyPublishers.ofByteArray(data)).build();
            var response = client.send(request,HttpResponse.BodyHandlers.ofByteArray());
            if (response.statusCode() == 200) {
                var labels = json.readValue(response.body(), String[].class);
                return java.util.Arrays.stream(labels).filter(allowed::contains).distinct().limit(3).toList();
            }
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        } catch (IOException ignored) {
            // If the optional local index is unavailable, direct table lookup and manual input still work.
        }
        return List.of();
    }

    Ranking search(String foodName, String cookingMethod) {
        if (endpoint == null) return null;
        try {
            byte[] data = json.writeValueAsBytes(Map.of("foodName", foodName,
                    "cookingMethod", cookingMethod == null ? "" : cookingMethod));
            var request = HttpRequest.newBuilder(endpoint.resolve("/search")).timeout(Duration.ofSeconds(8))
                    .header("Content-Type", "application/json").POST(HttpRequest.BodyPublishers.ofByteArray(data)).build();
            var response = client.send(request, HttpResponse.BodyHandlers.ofByteArray());
            if (response.statusCode() == 200) {
                Ranking ranking = json.readValue(response.body(), Ranking.class);
                if (ranking != null && ranking.matches() != null) return ranking;
            }
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        } catch (IOException ignored) {
            // The caller exposes the limited name-search fallback when the local encoder is unavailable.
        }
        return null;
    }
}
