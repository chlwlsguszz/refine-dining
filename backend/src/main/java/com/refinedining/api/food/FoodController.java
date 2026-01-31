package com.refinedining.api.food;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.web.bind.annotation.*;

@Slf4j
@RestController
@RequiredArgsConstructor
@RequestMapping("/api/food")
@CrossOrigin(origins = "http://localhost:5173")
public class FoodController {

}