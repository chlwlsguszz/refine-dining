package com.refinedining.api.weight;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.refinedining.domain.weight.MeasuredYieldCatalog;
import com.refinedining.domain.weight.MeasuredYieldService;
import com.refinedining.domain.weight.YieldNameSuggestions;
import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.ResultActions;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;

import java.util.Map;

import static org.hamcrest.Matchers.hasSize;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

class MeasuredYieldApiTest {
    final ObjectMapper json = new ObjectMapper();
    final MockMvc http;

    MeasuredYieldApiTest() throws Exception {
        var table = new MeasuredYieldCatalog(json);
        var service = new MeasuredYieldService(table,new YieldNameSuggestions(json,""));
        http = MockMvcBuilders.standaloneSetup(new WeightPredictionController(table,service)).build();
    }

    private ResultActions predict(Map<String,?> body) throws Exception {
        return http.perform(post("/api/weight/predict").contentType(MediaType.APPLICATION_JSON)
                .content(json.writeValueAsBytes(body)));
    }

    @Test void exposesThreeFatBracketsWithoutGuessing() throws Exception {
        predict(Map.of("foodName","소고기 패티","cookingMethod","팬구이","baseWeight",200))
                .andExpect(status().isOk()).andExpect(jsonPath("$.status").value("NEED_CONDITIONS"))
                .andExpect(jsonPath("$.candidates",hasSize(3))).andExpect(jsonPath("$.predictedWeight").isEmpty());
    }

    @Test void scalesPublishedMeanAndObservedRangeAfterConfirmation() throws Exception {
        predict(Map.of("foodName","닭 넓적다리","cookingMethod","오븐구이","evidenceId","usda-r2-05094","baseWeight",200))
                .andExpect(status().isOk()).andExpect(jsonPath("$.source").value("MEASURED_YIELD"))
                .andExpect(jsonPath("$.predictedWeight").value(138.0)).andExpect(jsonPath("$.minWeight").value(116.0))
                .andExpect(jsonPath("$.maxWeight").value(158.0)).andExpect(jsonPath("$.yieldPercent").value(69))
                .andExpect(jsonPath("$.evidence.sourceRow").value("Sheet1!A74:L74"))
                .andExpect(jsonPath("$.evidence.sampleCount").isEmpty());
    }

    @Test void acceptsOnlyMappedCodesAndRequiresConfirmation() throws Exception {
        predict(Map.of("foodCd","R209-008000701-0000","cookingMethod","오븐구이","baseWeight",200))
                .andExpect(status().isOk()).andExpect(jsonPath("$.status").value("NEED_CONDITIONS"))
                .andExpect(jsonPath("$.candidates[0].id").value("usda-r2-05094"));
        predict(Map.of("foodCd","R209-008000701-0000","foodName","옥수수","baseWeight",200))
                .andExpect(status().isOk()).andExpect(jsonPath("$.status").value("NO_MATCH"));
    }

    @Test void outOfScopeOrContradictoryConditionsNeverReturnAnEstimate() throws Exception {
        for (String name : new String[]{"옥수수","껍질 없는 닭 넓적다리"}) {
            predict(Map.of("foodName",name,"cookingMethod","오븐구이","baseWeight",200,
                    "rawProtein",25,"cookedProtein",29))
                    .andExpect(status().isOk()).andExpect(jsonPath("$.status").value("NO_MATCH"))
                    .andExpect(jsonPath("$.predictedWeight").isEmpty()).andExpect(jsonPath("$.candidates",hasSize(0)));
        }
        predict(Map.of("foodName","소고기 패티","cookingMethod","팬구이","baseWeight",150,"evidenceId","usda-r2-05094"))
                .andExpect(status().isBadRequest());
        predict(Map.of("foodName","닭 넓적다리","cookingMethod","튀기기","baseWeight",150,"evidenceId","usda-r2-05094"))
                .andExpect(status().isBadRequest());
    }

    @Test void rejectsInvalidPortionsAndMissingFood() throws Exception {
        for (Number weight : new Number[]{0, -1, 1_000_001, 0.0001}) {
            predict(Map.of("foodName","소고기 패티","baseWeight",weight)).andExpect(status().isBadRequest());
        }
        predict(Map.of("baseWeight",100)).andExpect(status().isBadRequest());
    }
}
