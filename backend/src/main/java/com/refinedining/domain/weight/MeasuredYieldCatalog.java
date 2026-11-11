package com.refinedining.domain.weight;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.core.io.ClassPathResource;
import org.springframework.stereotype.Component;

import java.io.IOException;
import java.io.InputStream;
import java.math.BigDecimal;
import java.text.Normalizer;
import java.util.*;

/** Read the versioned USDA table once. Only curated aliases and codes can authorize a selection. */
@Component
public class MeasuredYieldCatalog {
    public record Evidence(String id, String foodLabel, String methodLabel, String conditions, String rawBasis,
                           BigDecimal meanPercent, BigDecimal minPercent, BigDecimal maxPercent, Integer sampleCount,
                           String title, String sourceUrl, String sourceRow, String version,
                           String sourceDescription, String sourceMethod, String statisticNote) {}

    record Entry(Evidence source, Set<String> foods, Set<String> methods, Set<String> codes,
                 String species, String cut, String methodKey, Set<String> preparationTags) {}

    private final List<Entry> entries;

    public MeasuredYieldCatalog(ObjectMapper json) throws IOException {
        try (InputStream data = new ClassPathResource("cooking-yields.json").getInputStream()) {
            JsonNode catalog = json.readTree(data);
            List<Entry> loaded = new ArrayList<>();
            Set<String> ids = new HashSet<>();
            for (JsonNode row : catalog.required("records")) {
                String food = row.required("foodLabel").asText();
                String method = row.required("methodLabel").asText();
                var evidence = new Evidence(row.required("id").asText(), food, method, row.required("conditions").asText(),
                        row.required("rawBasis").asText(), number(row,"meanPercent"), number(row,"minPercent"),
                        number(row,"maxPercent"), row.path("sampleCount").isNumber() ? row.get("sampleCount").intValue() : null,
                        catalog.required("title").asText(), catalog.required("sourceUrl").asText(), row.required("sourceRow").asText(),
                        catalog.required("version").asText(), row.path("sourceDescription").asText(),
                        row.path("sourceMethod").asText(), row.path("statisticNote").asText(""));
                if (!ids.add(evidence.id()) || evidence.meanPercent() == null || evidence.meanPercent().signum() <= 0)
                    throw new IOException("Invalid measured cooking yield at " + evidence.sourceRow());
                loaded.add(new Entry(evidence, aliases(row,"foodAliases",food), aliases(row,"methodAliases",method),
                        aliases(row,"foodCodes",""), row.path("species").asText("unknown"),
                        row.path("cut").asText("unknown"), row.path("methodKey").asText("unknown"),
                        tags(row)));
            }
            if (loaded.isEmpty()) throw new IOException("Cooking yield table is empty.");
            entries = List.copyOf(loaded);
        }
    }

    private static BigDecimal number(JsonNode row, String key) {
        JsonNode value = row.path(key);
        return value.isNumber() ? value.decimalValue() : null;
    }

    static String key(String input) {
        return input == null ? "" : Normalizer.normalize(input, Normalizer.Form.NFKC)
                .toLowerCase(Locale.ROOT).replaceAll("[\\s_]+", "");
    }

    private static Set<String> aliases(JsonNode row, String field, String canonical) {
        Set<String> values = new HashSet<>();
        if (!canonical.isBlank()) values.add(key(canonical));
        row.path(field).forEach(value -> values.add(key(value.asText())));
        values.remove("");
        return Set.copyOf(values);
    }

    private static Set<String> tags(JsonNode row) {
        Set<String> values = new HashSet<>();
        row.path("preparationTags").forEach(value -> values.add(value.asText()));
        return Set.copyOf(values);
    }

    public List<Evidence> options() {
        return entries.stream().map(Entry::source).toList();
    }

    List<Entry> searchEntries() { return entries; }

    List<Evidence> candidates(String foodName, String foodCode, String cookingMethod) {
        String name = key(foodName), code = key(foodCode), method = key(cookingMethod);
        return entries.stream()
                .filter(entry -> code.isEmpty() || entry.codes().contains(code))
                .filter(entry -> name.isEmpty() || entry.foods().contains(name))
                .filter(entry -> method.isEmpty() || entry.methods().contains(method))
                .map(Entry::source).toList();
    }

    List<String> foodLabelsForMethod(String method) {
        String term = key(method);
        return entries.stream().filter(entry -> term.isEmpty() || entry.methods().contains(term))
                .map(entry -> entry.source().foodLabel()).distinct().toList();
    }
}
