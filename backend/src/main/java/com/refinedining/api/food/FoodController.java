package com.refinedining.api.food;

import com.refinedining.domain.food.refined.dto.FoodSearchResponse;
import com.refinedining.domain.food.refined.service.FoodSearchService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@Slf4j
@RestController
@RequiredArgsConstructor
@RequestMapping("/api/food")
@CrossOrigin(origins = "http://localhost:5173")
public class FoodController {

    private final FoodSearchService foodSearchService;

    @GetMapping("/search")
    public ResponseEntity<List<FoodSearchResponse>> search(@RequestParam String name,
                                                           @RequestParam(defaultValue = "0") int page,
                                                           @RequestParam(defaultValue = "10") int size) {

        return ResponseEntity.ok(foodSearchService.searchFood(name, page, size));
    }
}