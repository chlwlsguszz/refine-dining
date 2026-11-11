package com.refinedining.domain.weight;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.refinedining.api.weight.WeightPredictionController;
import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.ResultActions;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;

import java.util.List;
import java.util.Map;

import static org.hamcrest.Matchers.hasSize;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.*;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

class YieldSearchApiTest {
    private final ObjectMapper json = new ObjectMapper();
    private final YieldNameSuggestions retriever = mock(YieldNameSuggestions.class);
    private final MockMvc http;

    YieldSearchApiTest() throws Exception {
        var catalog = new MeasuredYieldCatalog(json);
        var service = new MeasuredYieldService(catalog, retriever, new YieldEvidenceSearch(catalog, retriever));
        http = MockMvcBuilders.standaloneSetup(new WeightPredictionController(catalog, service)).build();
        ranks("usda-r2-05094");
    }

    private void ranks(String... ids) {
        when(retriever.search(anyString(), anyString())).thenReturn(new YieldNameSuggestions.Ranking("E5",
                java.util.Arrays.stream(ids).map(id -> new YieldNameSuggestions.RankedEvidence(id, .88)).toList()));
    }

    private ResultActions request(String path, Map<String, ?> body) throws Exception {
        return http.perform(post("/api/weight/" + path).contentType(MediaType.APPLICATION_JSON)
                .content(json.writeValueAsBytes(body)));
    }

    @Test void freeTextReturnsEvidenceWithoutChangingTheQueryOrCalculating() throws Exception {
        request("search", Map.of("foodName", "닭다리살", "cookingMethod", "구이"))
                .andExpect(status().isOk()).andExpect(jsonPath("$.query").value("닭다리살"))
                .andExpect(jsonPath("$.sourceCount").value(173)).andExpect(jsonPath("$.engine").value("E5"))
                .andExpect(jsonPath("$.matches[0].evidence.id").value("usda-r2-05094"))
                .andExpect(jsonPath("$.matches[0].relation").value("REFERENCE"))
                .andExpect(jsonPath("$.matches[0].canEstimate").value(true))
                .andExpect(jsonPath("$.predictedWeight").doesNotExist());
        verify(retriever).search("닭다리살", "구이");
    }

    @Test void selectionRequiresExplicitReferenceConfirmationAndMembershipInCurrentResults() throws Exception {
        var query = new java.util.HashMap<String, Object>(Map.of("foodName", "닭다리살", "cookingMethod", "구이",
                "baseWeight", 200, "evidenceId", "usda-r2-05094"));
        request("predict", query).andExpect(status().isBadRequest());
        query.put("confirmReference", true);
        request("predict", query).andExpect(status().isOk()).andExpect(jsonPath("$.source").value("REFERENCE_YIELD"))
                .andExpect(jsonPath("$.predictedWeight").value(138.0));
        query.put("evidenceId", "usda-r2-23574");
        request("predict", query).andExpect(status().isBadRequest());
    }

    @Test void conflictingSkinCutAndMethodStayVisibleButCannotBeCalculated() throws Exception {
        for (var input : List.of(Map.of("foodName", "껍질 없는 닭 넓적다리", "cookingMethod", "구이"),
                Map.of("foodName", "닭 가슴", "cookingMethod", "구이"),
                Map.of("foodName", "닭 허벅지", "cookingMethod", "튀김"))) {
            request("search", input).andExpect(status().isOk())
                    .andExpect(jsonPath("$.matches[0].relation").value("INCOMPATIBLE"))
                    .andExpect(jsonPath("$.matches[0].canEstimate").value(false));
            var selected = new java.util.HashMap<String, Object>(input);
            selected.putAll(Map.of("baseWeight", 200, "evidenceId", "usda-r2-05094", "confirmReference", true));
            request("predict", selected).andExpect(status().isBadRequest());
        }
    }

    @Test void outOfCorpusQueryDoesNotReturnAnimalData() throws Exception {
        request("search", Map.of("foodName", "감자", "cookingMethod", "삶기"))
                .andExpect(status().isOk()).andExpect(jsonPath("$.matches", hasSize(0)));
        verify(retriever, never()).search(anyString(), anyString());
    }

    @Test void untrustedReturnedIdsAreFilteredAndExplicitFatConflictsAreRejected() throws Exception {
        ranks("unknown-record", "usda-r2-23574", "usda-r2-13496");
        request("search", Map.of("foodName", "소고기 패티 지방20%", "cookingMethod", "팬구이"))
                .andExpect(status().isOk()).andExpect(jsonPath("$.matches", hasSize(2)))
                .andExpect(jsonPath("$.matches[0].canEstimate").value(true))
                .andExpect(jsonPath("$.matches[1].canEstimate").value(false));
    }

    @Test void unavailableEncoderUsesClearlyLabelledNameFallback() throws Exception {
        when(retriever.search(anyString(), anyString())).thenReturn(null);
        request("search", Map.of("foodName", "소고기 안심", "cookingMethod", "구이"))
                .andExpect(status().isOk()).andExpect(jsonPath("$.engine").value("NAME"))
                .andExpect(jsonPath("$.matches[0].evidence.foodLabel").exists());
    }

    @Test void fatRangeMustFitOneSourceBracket() throws Exception {
        ranks("usda-r2-23564", "usda-r2-23574", "usda-r2-13496");
        var result = request("search", Map.of("foodName", "소고기 패티 지방 12% 미만", "cookingMethod", "팬구이"))
                .andExpect(status().isOk()).andReturn();
        var matches = json.readTree(result.getResponse().getContentAsString()).get("matches");
        for (var match : matches) {
            boolean lowFat = match.get("evidence").get("id").asText().equals("usda-r2-23564");
            org.junit.jupiter.api.Assertions.assertEquals(lowFat, match.get("canEstimate").asBoolean());
        }
    }

    @Test void explicitRibeyeDoesNotAuthorizeSirloinAndEnglishMethodsWork() throws Exception {
        var catalog = new MeasuredYieldCatalog(json);
        var sirloin = catalog.searchEntries().stream().filter(entry -> entry.species().equals("beef")
                && entry.cut().equals("sirloin") && entry.methodKey().equals("grill")).findFirst().orElseThrow();
        var ribeye = catalog.searchEntries().stream().filter(entry -> entry.species().equals("beef")
                && entry.cut().equals("ribeye") && entry.methodKey().equals("grill")).findFirst().orElseThrow();
        var conditions = new YieldQueryConditions("소고기 꽃등심", "grilled");
        org.junit.jupiter.api.Assertions.assertFalse(conditions.assess(sirloin).canEstimate());
        org.junit.jupiter.api.Assertions.assertTrue(conditions.assess(ribeye).canEstimate());
    }

    @Test void mixedDishRemainsUncalculableWhenEncoderIsDown() throws Exception {
        when(retriever.search(anyString(), anyString())).thenReturn(null);
        var result = request("search", Map.of("foodName", "닭고기 감자", "cookingMethod", "오븐구이"))
                .andExpect(status().isOk()).andReturn();
        for (var match : json.readTree(result.getResponse().getContentAsString()).get("matches"))
            org.junit.jupiter.api.Assertions.assertFalse(match.get("canEstimate").asBoolean());
    }
}
