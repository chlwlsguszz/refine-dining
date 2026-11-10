package com.refinedining.api.nutrition;

import com.fasterxml.jackson.databind.node.ObjectNode;
import com.refinedining.domain.nutrition.NutritionAnswers;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.*;
import java.util.Map;
import java.util.NoSuchElementException;

@RestController
@ConditionalOnProperty("rag.catalog")
public class NutritionAnswerController {
    private final NutritionAnswers answers;

    public NutritionAnswerController(NutritionAnswers answers) { this.answers = answers; }

    @PostMapping("/api/nutrition/answers")
    public ObjectNode ask(@RequestBody NutritionAnswers.Question question) { return answers.answer(question); }

    @ExceptionHandler(IllegalArgumentException.class) @ResponseStatus(HttpStatus.BAD_REQUEST)
    public Map<String,String> invalid(IllegalArgumentException e) { return Map.of("message",e.getMessage()); }
    @ExceptionHandler(NoSuchElementException.class) @ResponseStatus(HttpStatus.NOT_FOUND)
    public Map<String,String> missing(NoSuchElementException e) { return Map.of("message",e.getMessage()); }
}
