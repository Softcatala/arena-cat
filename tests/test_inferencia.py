import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml

from scripts import inferencia


class FakeInputs(dict):
    def __init__(self):
        super().__init__({"input_ids": [[1, 2]]})
        self.input_ids = inferencia.torch.tensor([[1, 2]])

    def to(self, device):
        self.device = device
        return self


class FakeTokenizer:
    eos_token_id = 99
    chat_template = "fake-template"

    def __init__(self):
        self.messages = None
        self.formatted_prompt = None
        self.decode_args = None

    def apply_chat_template(self, messages, tokenize, add_generation_prompt):
        self.messages = messages
        assert tokenize is False
        assert add_generation_prompt is True
        return "PROMPT"

    def __call__(self, formatted_prompt, return_tensors):
        self.formatted_prompt = formatted_prompt
        assert return_tensors == "pt"
        return FakeInputs()

    def decode(self, tokens, skip_special_tokens):
        self.decode_args = (tokens.tolist(), skip_special_tokens)
        return "Resposta final"


class FakeModel:
    device = "cpu"

    def __init__(self):
        self.generate_kwargs = None

    def generate(self, **kwargs):
        self.generate_kwargs = kwargs
        return inferencia.torch.tensor([[1, 2, 7, 8]])


class TestInferencia(unittest.TestCase):
    def test_load_prompts_accepts_text_dict_and_list(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            prompt_dir = root / "data" / "prompts" / "v1"
            prompt_dir.mkdir(parents=True)

            (prompt_dir / "text.yaml").write_text("Un prompt simple", encoding="utf-8")
            (prompt_dir / "dict.yaml").write_text(
                yaml.dump({"id": "dict-id", "text": "Prompt dict"}),
                encoding="utf-8",
            )
            (prompt_dir / "list.yaml").write_text(
                yaml.dump([{"id": "list-id", "text": "Prompt list"}]),
                encoding="utf-8",
            )

            prompts = inferencia.load_prompts(
                inferencia.discover_prompt_files(root),
                root=root,
            )

        self.assertEqual([p["id"] for p in prompts], ["dict-id", "list-id", "text"])
        self.assertEqual(prompts[2]["text"], "Un prompt simple")
        self.assertEqual(prompts[2]["_path_origen"], "data/prompts/v1/text.yaml")

    def test_get_dtype_accepts_supported_types(self):
        self.assertIs(inferencia.get_dtype("float16"), inferencia.torch.float16)
        self.assertIs(inferencia.get_dtype("bfloat16"), inferencia.torch.bfloat16)
        self.assertIs(inferencia.get_dtype("float32"), inferencia.torch.float32)

        with self.assertRaises(ValueError):
            inferencia.get_dtype("int8")

    def test_load_model_passes_mockable_parameters(self):
        calls = []

        def fake_loader(*args, **kwargs):
            calls.append((args, kwargs))
            return "MODEL"

        entry_model = {
            "id": "model-id",
            "model_name": "org/model",
            "revision": "main",
            "torch_dtype": "bfloat16",
            "device_map": "auto",
        }

        model = inferencia.load_model(
            entry_model,
            hf_token="hf_test",
            model_loader=fake_loader,
        )

        self.assertEqual(model, "MODEL")
        self.assertEqual(calls[0][0], ("org/model",))
        self.assertEqual(calls[0][1]["revision"], "main")
        self.assertIs(calls[0][1]["dtype"], inferencia.torch.bfloat16)
        self.assertEqual(calls[0][1]["device_map"], "auto")
        self.assertEqual(calls[0][1]["token"], "hf_test")

    def test_load_model_configures_4bit_quantization(self):
        calls = []

        def fake_loader(*args, **kwargs):
            calls.append((args, kwargs))
            return "MODEL"

        entry_model = {
            "id": "model-id",
            "model_name": "org/model",
            "revision": "main",
            "torch_dtype": "bfloat16",
            "device_map": "auto",
            "quantization": "4bit",
        }

        inferencia.load_model(entry_model, model_loader=fake_loader)

        quant_config = calls[0][1]["quantization_config"]
        self.assertTrue(quant_config.load_in_4bit)
        self.assertIs(quant_config.bnb_4bit_compute_dtype, inferencia.torch.bfloat16)
        self.assertEqual(quant_config.bnb_4bit_quant_type, "nf4")

    def test_apply_device_map_override_updates_all_models(self):
        config = {
            "models": [
                {"id": "model-1", "device_map": "auto"},
                {"id": "model-2", "device_map": "cpu"},
            ]
        }

        result = inferencia.apply_device_map_override(config, "cpu")

        self.assertIs(result, config)
        self.assertEqual(
            [model["device_map"] for model in result["models"]],
            ["cpu", "cpu"],
        )

    def test_apply_device_map_override_keeps_config_when_missing(self):
        config = {"models": [{"id": "model-1", "device_map": "auto"}]}

        result = inferencia.apply_device_map_override(config, None)

        self.assertIs(result, config)
        self.assertEqual(result["models"][0]["device_map"], "auto")

    def test_build_messages_adds_system_prompt_when_present(self):
        messages = inferencia.build_messages(
            "Hola",
            {"system_prompt": "Respon en catala"},
        )

        self.assertEqual(
            messages,
            [
                {"role": "system", "content": "Respon en catala"},
                {"role": "user", "content": "Hola"},
            ],
        )

    def test_generate_text_uses_tokenizer_and_model_without_hf(self):
        tokenizer = FakeTokenizer()
        model = FakeModel()
        generation_params = {
            "system_prompt": "Sistema",
            "max_new_tokens": 12,
            "temperature": 0,
            "top_p": 0.9,
        }

        text = inferencia.generate_text(
            tokenizer, model, "Usuari", generation_params
        )

        self.assertEqual(text, "Resposta final")
        self.assertEqual(tokenizer.formatted_prompt, "PROMPT")
        self.assertEqual(
            tokenizer.messages,
            [
                {"role": "system", "content": "Sistema"},
                {"role": "user", "content": "Usuari"},
            ],
        )
        self.assertFalse(model.generate_kwargs["do_sample"])
        self.assertNotIn("temperature", model.generate_kwargs)
        self.assertNotIn("top_p", model.generate_kwargs)
        self.assertTrue(model.generate_kwargs["remove_invalid_values"])
        self.assertEqual(model.generate_kwargs["max_new_tokens"], 12)
        self.assertEqual(tokenizer.decode_args, ([7, 8], True))

    def test_generate_text_passes_sampling_parameters_when_temperature_is_positive(self):
        tokenizer = FakeTokenizer()
        model = FakeModel()
        generation_params = {
            "max_new_tokens": 12,
            "temperature": 0.7,
            "top_p": 0.9,
        }

        inferencia.generate_text(tokenizer, model, "Usuari", generation_params)

        self.assertTrue(model.generate_kwargs["do_sample"])
        self.assertEqual(model.generate_kwargs["temperature"], 0.7)
        self.assertEqual(model.generate_kwargs["top_p"], 0.9)

    def test_build_result_splits_reasoning_and_metadata(self):
        resultat = inferencia.build_result(
            prompt={
                "id": "prompt-1",
                "text": "Text prompt",
                "_path_origen": "data/prompts/v1/prompt-1.yaml",
            },
            model_entry={
                "id": "model-1",
                "model_name": "org/model",
                "revision": "abc",
            },
            generation_params={
                "temperature": 0.7,
                "top_p": 0.9,
                "max_new_tokens": 128,
            },
            global_config={
                "seed": 42,
                "backend_preferit": "transformers",
            },
            generated_text="<think>raons</think>Resposta",
            current_timestamp="2026-06-20T10:00:00Z",
            git_commit="abc123",
        )

        self.assertEqual(resultat["output"]["answer"], "Resposta")
        self.assertEqual(resultat["reasoning"]["content"], "raons")
        self.assertEqual(
            resultat["prompt"]["sha256"],
            inferencia.calculate_sha256("Text prompt"),
        )
        self.assertEqual(resultat["model"]["model_name"], "org/model")

    def test_run_pipeline_does_not_load_models_when_there_are_no_prompts(self):
        config = {
            "configuracio_global": {"seed": 42, "backend_preferit": "transformers"},
            "parametres_generacio": {},
            "models": [{"id": "model-id", "model_name": "org/model"}],
        }

        with patch.object(inferencia, "load_config", return_value=config), \
             patch.object(inferencia, "discover_prompt_files", return_value=[]), \
             patch.object(inferencia, "run_model") as run_model, \
             patch.object(inferencia.LOGGER, "error") as log_error:
            inferencia.run_pipeline(root=Path("/tmp/no-prompts"))

        run_model.assert_not_called()
        log_error.assert_called_once_with("No s'han trobat prompts")

    def test_run_pipeline_with_mock_model_saves_result(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            config_dir = root / "config" / "inferencia"
            prompt_dir = root / "data" / "prompts" / "v1"
            config_dir.mkdir(parents=True)
            prompt_dir.mkdir(parents=True)

            (prompt_dir / "prompt.yaml").write_text("Digues hola", encoding="utf-8")
            (config_dir / "inferencia_config.yaml").write_text(
                yaml.dump(
                    {
                        "configuracio_global": {
                            "seed": 42,
                            "backend_preferit": "transformers",
                        },
                        "parametres_generacio": {
                            "system_prompt": "Sistema",
                            "max_new_tokens": 12,
                            "temperature": 0,
                            "top_p": 1.0,
                        },
                        "models": [
                            {
                                "id": "fake-model",
                                "model_name": "org/fake-model",
                                "revision": "main",
                                "torch_dtype": "float32",
                                "device_map": "cpu",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            with patch.object(inferencia, "get_git_commit", return_value="git123"), \
                 patch.object(inferencia, "timestamp_utc", return_value="2026-06-20T10:00:00Z"), \
                 patch.object(inferencia.LOGGER, "info"):
                inferencia.run_pipeline(
                    root=root,
                    device_map="cpu",
                    tokenizer_loader=lambda *args, **kwargs: FakeTokenizer(),
                    model_loader=lambda *args, **kwargs: FakeModel(),
                )

            output_path = root / "data" / "inferencies" / "v1" / "fake-model" / "prompt.yaml"
            resultat = yaml.safe_load(output_path.read_text(encoding="utf-8"))

        self.assertEqual(resultat["output"]["answer"], "Resposta final")
        self.assertEqual(resultat["run"]["git_commit"], "git123")
        self.assertEqual(resultat["model"]["model_name"], "org/fake-model")


if __name__ == "__main__":
    unittest.main()
