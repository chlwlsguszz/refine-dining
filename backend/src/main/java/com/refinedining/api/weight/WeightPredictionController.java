package com.refinedining.api.weight;

import com.refinedining.domain.weight.MeasuredYieldCatalog;
import com.refinedining.domain.weight.MeasuredYieldService;
import com.refinedining.domain.weight.YieldEvidenceSearch;
import jakarta.validation.Valid;
import org.springframework.http.HttpStatus;
import org.springframework.http.converter.HttpMessageNotReadableException;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/weight")
@CrossOrigin(origins = "http://localhost:5173")
public class WeightPredictionController {
    private final MeasuredYieldCatalog catalog;
    private final MeasuredYieldService service;

    public WeightPredictionController(MeasuredYieldCatalog catalog, MeasuredYieldService service) {
        this.catalog = catalog;
        this.service = service;
    }

    @GetMapping("/options")
    public List<MeasuredYieldCatalog.Evidence> options() { return catalog.options(); }

    @PostMapping("/search")
    public YieldEvidenceSearch.Result search(@Valid @RequestBody MeasuredYieldService.SearchQuery input) {
        return service.search(input);
    }

    @PostMapping("/predict")
    public MeasuredYieldService.Prediction predict(@Valid @RequestBody MeasuredYieldService.Query input) {
        return service.predict(input);
    }

    @ExceptionHandler(IllegalArgumentException.class)
    @ResponseStatus(HttpStatus.BAD_REQUEST)
    public Map<String,String> invalidSelection(IllegalArgumentException error) {
        return Map.of("message",error.getMessage());
    }

    @ExceptionHandler(HttpMessageNotReadableException.class)
    @ResponseStatus(HttpStatus.BAD_REQUEST)
    public Map<String,String> invalidRequest() { return Map.of("message","식품과 생중량(g)을 확인해 주세요."); }
}
