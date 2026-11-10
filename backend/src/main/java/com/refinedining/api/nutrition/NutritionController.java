package com.refinedining.api.nutrition;

import com.fasterxml.jackson.databind.node.ObjectNode;
import com.refinedining.domain.nutrition.NutritionCatalog;
import com.refinedining.domain.nutrition.NutritionReviews;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.*;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.List;
import java.util.Map;
import java.util.NoSuchElementException;

@RestController
@ConditionalOnProperty("rag.catalog")
public class NutritionController {
    private final NutritionCatalog catalog;
    private final NutritionReviews reviews;
    private final String adminKey;

    public NutritionController(NutritionCatalog catalog, NutritionReviews reviews, @Value("${admin.api-key:${ADMIN_API_KEY:}}") String adminKey) {
        this.catalog = catalog;
        this.reviews = reviews;
        this.adminKey = adminKey;
    }

    @GetMapping("/api/nutrition/foods")
    public List<NutritionCatalog.Choice> search(@RequestParam String name) { return catalog.search(name); }

    @GetMapping("/api/nutrition/foods/{code}")
    public ObjectNode food(@PathVariable String code, @RequestParam(required = false) String version) {
        if (version != null && !catalog.version().equals(version)) throw new NoSuchElementException("다른 자료 버전입니다.");
        return catalog.food(code);
    }

    @GetMapping("/api/admin/nutrition/proposals")
    public List<ObjectNode> proposals(@RequestHeader(name="X-Admin-Key", required=false) String key) {
        checkKey(key);
        return reviews.all();
    }

    @PostMapping("/api/admin/nutrition/proposals/{id}")
    public ObjectNode review(@RequestHeader(name="X-Admin-Key", required=false) String key, @PathVariable String id,
                             @RequestBody NutritionReviews.Decision decision) {
        checkKey(key);
        return reviews.review(id, decision);
    }

    private void checkKey(String key) {
        if (adminKey.isBlank() || key == null || !MessageDigest.isEqual(adminKey.getBytes(StandardCharsets.UTF_8),
                key.getBytes(StandardCharsets.UTF_8))) throw new SecurityException("관리자 키를 확인하세요.");
    }

    @ExceptionHandler(SecurityException.class) @ResponseStatus(HttpStatus.FORBIDDEN)
    public Map<String,String> forbidden(SecurityException e) { return Map.of("message",e.getMessage()); }
    @ExceptionHandler(NoSuchElementException.class) @ResponseStatus(HttpStatus.NOT_FOUND)
    public Map<String,String> missing(NoSuchElementException e) { return Map.of("message",e.getMessage()); }
    @ExceptionHandler(IllegalArgumentException.class) @ResponseStatus(HttpStatus.BAD_REQUEST)
    public Map<String,String> invalid(IllegalArgumentException e) { return Map.of("message",e.getMessage()); }
}
