import collections, sys, unittest
sys.path.insert(0, 'scripts')
import recall_names as R

ENGLISH = {'sense', 'modern', 'paper', 'mini', 'desktop', 'river', 'portal'}
class Names(unittest.TestCase):
    def names(self, multi=(), single=()):
        return R.clean_names(collections.Counter(dict.fromkeys(multi, 9)), collections.Counter(dict.fromkeys(single, 9)), ENGLISH)
    def test_keeps_distinctive_two_word_names(self):
        self.assertIn('orange pi', self.names(multi=['orange pi'])[0])
    def test_drops_names_ending_in_a_generic_noun(self):
        self.assertEqual(self.names(multi=['dell laptop', 'samsung tv'])[0], [])
    def test_drops_cars_and_software_in_multi_word_names(self):
        self.assertEqual(self.names(multi=['toyota corolla', 'mozilla firefox', 'microsoft windows', 'tesla model'])[0], [])
    def test_keeps_distinctive_capitalized_single_names(self):
        self.assertIn('Keychron', self.names(single=['Keychron'])[1])
    def test_drops_english_words_even_when_capitalized(self):
        self.assertEqual(self.names(single=['Sense', 'Modern', 'Portal'])[1], [])
    def test_drops_companies_cars_and_software_as_single_names(self):
        self.assertEqual(self.names(single=['Toyota', 'Walmart', 'Costco', 'Mozilla', 'Firefox', 'Verizon', 'Waymo', 'Subaru'])[1], [])
    def test_rare_names_are_dropped(self):
        m = collections.Counter({'orange pi': 1}); s = collections.Counter({'Keychron': 1})
        self.assertEqual(R.clean_names(m, s, ENGLISH), ([], []))
class Nicknames(unittest.TestCase):
    def test_nicknames_seen_in_the_probe_match(self):
        for text in ('my mbp is great', 'typing on my mbpro now', 'an old rpi', 'bought a t470 for cheap', 'a mac book pro', 'my x1 carbon'):
            self.assertRegex(text, R.NICKNAMES, text)
    def test_nicknames_do_not_match_inside_words(self):
        for text in ('t470ish', 'the rpinext project', 'smbp protocol'):
            self.assertNotRegex(text, R.NICKNAMES, text)
if __name__ == '__main__': unittest.main()
