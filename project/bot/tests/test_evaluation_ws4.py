import unittest
from project.bot.evaluation import metrics


class EvaluationTests(unittest.TestCase):
    def test_unlabelled_is_not_success(self):
        self.assertIsNone(metrics.generation([{'annotations':None}])['groundedness'])
        self.assertIsNone(metrics.conversation([{'passed':None}])['pass_rate'])
        self.assertIsNone(metrics.retrieval([])['ndcg'])

    def test_labelled_results(self):
        result = metrics.generation([{'annotations':{'total_claims':4,'supported_claims':3,
                                                     'unsupported_claims':1,'relevance':.5}}])
        self.assertEqual(result['groundedness'],.75)
        self.assertEqual(result['hallucination_rate'],.25)
        self.assertEqual(metrics.conversation([{'passed':True},{'passed':False}])['pass_rate'],.5)
        self.assertEqual(metrics.retrieval([{'predicted':['a','b'],'relevance':{'a':2,'c':1}}],2)['recall'],.5)

    def test_invalid_labels(self):
        with self.assertRaises(ValueError):
            metrics.conversation([{'passed':'yes'}])
        with self.assertRaises(ValueError):
            metrics.generation([{'annotations':{'total_claims':1,'supported_claims':2,
                                                'unsupported_claims':0,'relevance':1}}])
