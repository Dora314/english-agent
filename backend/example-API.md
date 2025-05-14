# AI Data Processing and Display Workflow

This document outlines the key code segments involved in sending requests to the AI, processing the AI's response, and displaying the information on the user interface.

## 1. Calling the AI and Formatting Output (Backend)

The function `strict_output` in `src/lib/gpt.ts` is responsible for interacting with the Gemini AI model. It sends a prompt and specifies the desired JSON output format. It includes retry logic and error handling to ensure a valid JSON response.

```typescript
// filepath: e:\Source\quiz\quiz\src\lib\gpt.ts
// ...existing code...
export async function strict_output(
  system_prompt: string,
  user_prompt: QuizData | QuizData[],
  output_format: OutputFormat,
  default_category: string = "",
  output_value_only: boolean = false,
  model: string = "gemini-1.5-flash-002",
  temperature: number = 1,
  num_tries: number = 3,
  verbose: boolean = false
): Promise<
  {
    question: string;
    answer: string;
  }[]
> {
  // ...existing code...
  for (let i = 0; i < num_tries; i++) {
    let output_format_prompt: string = `\nYou are to output the following in json format: ${JSON.stringify(
      output_format
    )}.\nDo not use code block delimiters like \`\`\`json or \`\`\` in your response. Do not put quotation marks or escape character \\ in the output fields.`;
    // ...existing code...
    try {
      const prompt =
        system_prompt +
        output_format_prompt +
        error_msg +
        (typeof user_prompt === "string"
          ? `\n${user_prompt}`
          : `\n${JSON.stringify(user_prompt)}`);

      const modelInstance = genAI.getGenerativeModel({ model });

      const result = await modelInstance.generateContent(prompt);

      let res: string = result.response.text().replace(/'/g, '"');

      res = res.replace(/(\w)"(\w)/g, "$1'$2");

      // ...existing code...
      try {
        let output: any = JSON.parse(res);
        // ... (logic to validate and structure output based on output_format) ...
        return list_input ? output : output[0];
      } catch (e) {
        error_msg = `\n\nResult: ${res}\n\nError message: ${e}`;
        console.log("An exception occurred:", e);
        console.log("Current invalid json format:", res);
      }
    } catch (error) {
      console.error(`Attempt ${i + 1} failed:`, error);
    }
  }
  return [];
}
```

## 2. API Endpoint for Question Generation (Backend)

The `POST /api/questions` route defined in `src/app/api/questions/route.ts` handles requests for generating questions. It calls `strict_output` with the appropriate prompts and returns the generated questions.

```typescript
// filepath: e:\Source\quiz\quiz\src\app\api\questions\route.ts
// ...existing code...
export async function POST(req: Request, res: Response) {
  try {
    // ... (authentication and request body parsing) ...
    const { amount, topic, type } = getQuestionsSchema.parse(body);
    let questions: any;
    if (type === "open_ended") {
      questions = await strict_output(
        "You are a helpful AI that is able to generate a pair of question and answers, the length of each answer should not be more than 15 words, store all the pairs of answers and questions in a JSON array",
        new Array(amount).fill(
          `You are to generate a random hard open-ended questions about ${topic}`
        ),
        {
          question: "question",
          answer: "answer with max length of 15 words",
        }
      );
    } else if (type === "mcq") {
      questions = await strict_output(
        // ... (prompt for MCQ) ...
        {
          question: "question",
          answer: "answer with max length of 15 words",
          option1: "option1 with max length of 15 words",
          option2: "option2 with max length of 15 words",
          option3: "option3 with max length of 15 words",
        }
      );
    }
    return NextResponse.json(
      {
        questions: questions,
      },
      {
        status: 200,
      }
    );
  } catch (error) {
    // ... (error handling) ...
  }
}
```

## 3. API Endpoint for Game Creation and Saving Questions (Backend)

The `POST /api/game` route in `src/app/api/game/route.ts` creates a new game entry in the database. It then calls the `/api/questions` endpoint to fetch questions from the AI. These questions are processed (e.g., shuffling MCQ options) and saved to the database.

```typescript
// filepath: e:\Source\quiz\quiz\src\app\api\game\route.ts
// ...existing code...
export async function POST(req: Request, res: Response) {
  try {
    // ... (authentication and request body parsing) ...
    const game = await prisma.game.create({
      data: {
        gameType: type,
        timeStarted: new Date(),
        userId: session.user.id,
        topic,
      },
    });
    // ... (update topic_count) ...

    const { data } = await axios.post(
      `${process.env.API_URL as string}/api/questions`,
      {
        amount,
        topic,
        type,
      }
    );

    if (type === "mcq") {
      type mcqQuestion = {
        question: string;
        answer: string;
        option1: string;
        option2: string;
        option3: string;
      };

      const manyData = data.questions.map((question: mcqQuestion) => {
        const options = [
          question.option1,
          question.option2,
          question.option3,
          question.answer,
        ].sort(() => Math.random() - 0.5);
        return {
          question: question.question,
          answer: question.answer,
          options: JSON.stringify(options),
          gameId: game.id,
          questionType: "mcq",
        };
      });

      await prisma.question.createMany({
        data: manyData,
      });
    } else if (type === "open_ended") {
      // ... (handle open_ended questions) ...
    }

    return NextResponse.json({ gameId: game.id }, { status: 200 });
  } catch (error) {
    // ... (error handling) ...
  }
}
```

## 4. Sending Quiz Creation Request from UI (Frontend)

The `QuizCreation` component (in `src/components/forms/QuizCreation.tsx`) uses `@tanstack/react-query`'s `useMutation` hook to call the `/api/game` endpoint when the user submits the quiz creation form.

```tsx
// filepath: e:\Source\quiz\quiz\src\components\forms\QuizCreation.tsx
// ...existing code...
const QuizCreation = ({ topic: topicParam }: Props) => {
  const router = useRouter();
  const [showLoader, setShowLoader] = React.useState(false);
  const [finishedLoading, setFinishedLoading] = React.useState(false);
  const { toast } = useToast();
  const { mutate: getQuestions, isLoading } = useMutation({
    mutationFn: async ({ amount, topic, type }: Input) => {
      const response = await axios.post("/api/game", { amount, topic, type });
      return response.data;
    },
  });

  const form = useForm<Input>({
    // ... (form setup) ...
  });

  const onSubmit = async (data: Input) => {
    setShowLoader(true);
    getQuestions(data, {
      onError: (error) => {
        // ... (error handling) ...
      },
      onSuccess: ({ gameId }: { gameId: string }) => {
        setFinishedLoading(true);
        setTimeout(() => {
          if (form.getValues("type") === "mcq") {
            router.push(`/play/mcq/${gameId}`);
          } else if (form.getValues("type") === "open_ended") {
            router.push(`/play/open-ended/${gameId}`);
          }
        }, 2000);
      },
    });
  };
  // ...existing code...
  if (showLoader) {
    return <LoadingQuestions finished={finishedLoading} />;
  }

  return (
    // ... (form JSX) ...
  );
};

export default QuizCreation;
```

## 5. Displaying MCQ Questions (Frontend)

The `MCQ` component (in `src/components/MCQ.tsx`) receives game data, including questions, as props. It parses the JSON string of options for the current MCQ question and renders them.

```tsx
// filepath: e:\Source\quiz\quiz\src\components\MCQ.tsx
// ...existing code...
const MCQ = ({ game }: Props) => {
  // ... (state and hooks) ...

  const currentQuestion = React.useMemo(() => {
    return game.questions[questionIndex];
  }, [questionIndex, game.questions]);

  const options = React.useMemo(() => {
    if (!currentQuestion) return [];
    if (!currentQuestion.options) return [];
    return JSON.parse(currentQuestion.options as string) as string[];
  }, [currentQuestion]);

  // ... (event handlers and effects) ...

  return (
    <div className="absolute -translate-x-1/2 -translate-y-1/2 md:w-[80vw] max-w-4xl w-[90vw] top-1/2 left-1/2">
      {/* ... (game info display) ... */}
      <Card className="w-full mt-4">
        <CardHeader className="flex flex-row items-center">
          <CardTitle className="mr-5 text-center divide-y divide-zinc-600/50">
            <div>{questionIndex + 1}</div>
            <div className="text-base text-slate-400">
              {game.questions.length}
            </div>
          </CardTitle>
          <CardDescription className="flex-grow text-lg">
            {currentQuestion?.question}
          </CardDescription>
        </CardHeader>
      </Card>
      <div className="flex flex-col items-center justify-center w-full mt-4">
        {options.map((option, index) => {
          return (
            <Button
              key={option}
              variant={selectedChoice === index ? "default" : "outline"}
              className="justify-start w-full py-8 mb-4"
              onClick={() => setSelectedChoice(index)}
            >
              <div className="flex items-center justify-start">
                <div className="p-2 px-3 mr-5 border rounded-md">
                  {index + 1}
                </div>
                <div className="text-start">{option}</div>
              </div>
            </Button>
          );
        })}
        {/* ... (Next button) ... */}
      </div>
    </div>
  );
};

export default dynamic(() => Promise.resolve(MCQ), { ssr: false });
```

## 6. Displaying Open-Ended Questions (Frontend)

The `OpenEnded` component (in `src/components/OpenEnded.tsx`) uses a child component `BlankAnswerInput` to render the question and provide input fields for the user.

### `OpenEnded.tsx`

```tsx
// filepath: e:\Source\quiz\quiz\src\components\OpenEnded.tsx
// ...existing code...
const OpenEnded = ({ game }: Props) => {
  // ... (state and hooks) ...
  const currentQuestion = React.useMemo(() => {
    return game.questions[questionIndex];
  }, [questionIndex, game.questions]);

  // ... (event handlers and effects) ...

  return (
    <div className="absolute -translate-x-1/2 -translate-y-1/2 md:w-[80vw] max-w-4xl w-[90vw] top-1/2 left-1/2">
      {/* ... (game info display) ... */}
      <Card className="w-full mt-4">
        <CardHeader className="flex flex-row items-center">
          {/* ... (question number) ... */}
          <CardDescription className="flex-grow text-lg">
            {currentQuestion?.question}
          </CardDescription>
        </CardHeader>
      </Card>
      <div className="flex flex-col items-center justify-center w-full mt-4">
        {currentQuestion && currentQuestion.answer && (
          <BlankAnswerInput
            setBlankAnswer={setBlankAnswer}
            answer={currentQuestion.answer}
          />
        )}
        {/* ... (Next button) ... */}
      </div>
    </div>
  );
};

export default OpenEnded;
```

### `BlankAnswerInput.tsx`

This component (in `src/components/BlankAnswerInput.tsx`) takes the correct answer, extracts keywords, and replaces them with input blanks in the displayed question.

```tsx
// filepath: e:\Source\quiz\quiz\src\components\BlankAnswerInput.tsx
// ...existing code...
const BlankAnswerInput = ({ answer, setBlankAnswer }: Props) => {
  const keywords = React.useMemo(() => {
    const words = keyword_extractor.extract(answer, {
      // ... (keyword extraction options) ...
    });
    const shuffled = words.sort(() => 0.5 - Math.random());
    return shuffled.slice(0, 2);
  }, [answer]);

  const answerWithBlanks = React.useMemo(() => {
    const answerWithBlanks = keywords.reduce((acc, curr) => {
      return acc.replaceAll(curr, blank);
    }, answer);
    setBlankAnswer(answerWithBlanks);
    return answerWithBlanks;
  }, [answer, keywords, setBlankAnswer]);

  return (
    <div className="flex justify-start w-full mt-4">
      <h1 className="text-xl font-semibold">
        {answerWithBlanks &&
          answerWithBlanks.split(blank).map((part, index) => {
            return (
              <React.Fragment key={index}>
                {part}
                {index === answerWithBlanks.split(blank).length - 1 ? (
                  ""
                ) : (
                  <input
                    id="user-blank-input"
                    className="text-center border-b-2 border-black dark:border-white w-28 focus:border-2 focus:border-b-4 focus:outline-none"
                    type="text"
                  />
                )}
              </React.Fragment>
            );
          })}
      </h1>
    </div>
  );
};

export default BlankAnswerInput;
```
