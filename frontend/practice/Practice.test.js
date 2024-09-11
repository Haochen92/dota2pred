import {render, screen, waitFor} from '@testing-library/react';
import '@testing-library/jest-dom';
import userEvent from '@testing-library/user-event'; 
import { Pokemon } from './Practice';

beforeEach(() => {
  global.fetch = jest.fn((url) => {
    // Mock the Pokémon list endpoint
    if (url === 'https://pokeapi.co/api/v2/pokemon/?limit=20&offset=0') {
      return Promise.resolve({
        json: () =>
          Promise.resolve({
            results: [
              { name: 'bulbasaur', url: 'https://pokeapi.co/api/v2/pokemon/bulbasaur' },
              { name: 'ivysaur', url: 'https://pokeapi.co/api/v2/pokemon/ivysaur' },
              { name: 'venusaur', url: 'https://pokeapi.co/api/v2/pokemon/venusaur' },
              { name: 'charmander', url: 'https://pokeapi.co/api/v2/pokemon/charmander' },
              { name: 'charmeleon', url: 'https://pokeapi.co/api/v2/pokemon/charmeleon' },
              { name: 'charizard', url: 'https://pokeapi.co/api/v2/pokemon/charizard' },
              { name: 'squirtle', url: 'https://pokeapi.co/api/v2/pokemon/squirtle' },
              { name: 'wartortle', url: 'https://pokeapi.co/api/v2/pokemon/wartortle' },
              { name: 'blastoise', url: 'https://pokeapi.co/api/v2/pokemon/blastoise' },
              { name: 'caterpie', url: 'https://pokeapi.co/api/v2/pokemon/caterpie' },
              { name: 'metapod', url: 'https://pokeapi.co/api/v2/pokemon/metapod' },
              { name: 'butterfree', url: 'https://pokeapi.co/api/v2/pokemon/butterfree' },
              { name: 'weedle', url: 'https://pokeapi.co/api/v2/pokemon/weedle' },
              { name: 'kakuna', url: 'https://pokeapi.co/api/v2/pokemon/kakuna' },
              { name: 'beedrill', url: 'https://pokeapi.co/api/v2/pokemon/beedrill' },
              { name: 'pidgey', url: 'https://pokeapi.co/api/v2/pokemon/pidgey' },
              { name: 'pidgeotto', url: 'https://pokeapi.co/api/v2/pokemon/pidgeotto' },
              { name: 'pidgeot', url: 'https://pokeapi.co/api/v2/pokemon/pidgeot' },
              { name: 'rattata', url: 'https://pokeapi.co/api/v2/pokemon/rattata' },
              { name: 'raticate', url: 'https://pokeapi.co/api/v2/pokemon/raticate' },
            ],
          }),
      });
    }

    // Mock individual Pokémon details endpoints
    if (url.includes('bulbasaur')) {
      return Promise.resolve({
        json: () =>
          Promise.resolve({
            sprites: { front_default: 'bulbasaur_image_url' },
          }),
      });
    }
    if (url.includes('ivysaur')) {
      return Promise.resolve({
        json: () =>
          Promise.resolve({
            sprites: { front_default: 'ivysaur_image_url' },
          }),
      });
    }
    if (url.includes('venusaur')) {
      return Promise.resolve({
        json: () =>
          Promise.resolve({
            sprites: { front_default: 'venusaur_image_url' },
          }),
      });
    }
    if (url.includes('charmander')) {
      return Promise.resolve({
        json: () =>
          Promise.resolve({
            sprites: { front_default: 'charmander_image_url' },
          }),
      });
    }
    if (url.includes('charmeleon')) {
      return Promise.resolve({
        json: () =>
          Promise.resolve({
            sprites: { front_default: 'charmeleon_image_url' },
          }),
      });
    }
    if (url.includes('charizard')) {
      return Promise.resolve({
        json: () =>
          Promise.resolve({
            sprites: { front_default: 'charizard_image_url' },
          }),
      });
    }
    if (url.includes('squirtle')) {
      return Promise.resolve({
        json: () =>
          Promise.resolve({
            sprites: { front_default: 'squirtle_image_url' },
          }),
      });
    }
    if (url.includes('wartortle')) {
      return Promise.resolve({
        json: () =>
          Promise.resolve({
            sprites: { front_default: 'wartortle_image_url' },
          }),
      });
    }
    if (url.includes('blastoise')) {
      return Promise.resolve({
        json: () =>
          Promise.resolve({
            sprites: { front_default: 'blastoise_image_url' },
          }),
      });
    }
    if (url.includes('caterpie')) {
      return Promise.resolve({
        json: () =>
          Promise.resolve({
            sprites: { front_default: 'caterpie_image_url' },
          }),
      });
    }
    if (url.includes('metapod')) {
      return Promise.resolve({
        json: () =>
          Promise.resolve({
            sprites: { front_default: 'metapod_image_url' },
          }),
      });
    }
    if (url.includes('butterfree')) {
      return Promise.resolve({
        json: () =>
          Promise.resolve({
            sprites: { front_default: 'butterfree_image_url' },
          }),
      });
    }
    if (url.includes('weedle')) {
      return Promise.resolve({
        json: () =>
          Promise.resolve({
            sprites: { front_default: 'weedle_image_url' },
          }),
      });
    }
    if (url.includes('kakuna')) {
      return Promise.resolve({
        json: () =>
          Promise.resolve({
            sprites: { front_default: 'kakuna_image_url' },
          }),
      });
    }
    if (url.includes('beedrill')) {
      return Promise.resolve({
        json: () =>
          Promise.resolve({
            sprites: { front_default: 'beedrill_image_url' },
          }),
      });
    }
    if (url.includes('pidgey')) {
      return Promise.resolve({
        json: () =>
          Promise.resolve({
            sprites: { front_default: 'pidgey_image_url' },
          }),
      });
    }
    if (url.includes('pidgeotto')) {
      return Promise.resolve({
        json: () =>
          Promise.resolve({
            sprites: { front_default: 'pidgeotto_image_url' },
          }),
      });
    }
    if (url.includes('pidgeot')) {
      return Promise.resolve({
        json: () =>
          Promise.resolve({
            sprites: { front_default: 'pidgeot_image_url' },
          }),
      });
    }
    if (url.includes('rattata')) {
      return Promise.resolve({
        json: () =>
          Promise.resolve({
            sprites: { front_default: 'rattata_image_url' },
          }),
      });
    }
    if (url.includes('raticate')) {
      return Promise.resolve({
        json: () =>
          Promise.resolve({
            sprites: { front_default: 'raticate_image_url' },
          }),
      });
    }

    // If no URL matches, return an error
    return Promise.reject(new Error('Unknown endpoint'));
  });
});

test('mocks fetch requests and displays data correctly', async () => {
  // Render the component
  render(<Pokemon />);

  // Wait for the fetch calls to complete and verify the fetched data
  await waitFor(() => {
    expect(screen.getByText('bulbasaur')).toBeInTheDocument();
    expect(screen.getByText('ivysaur')).toBeInTheDocument();
    expect(screen.getByText('venusaur')).toBeInTheDocument();
    expect(screen.getByText('charmander')).toBeInTheDocument();
  });
});


test("Testing Pagination Feature", async () => {
    render(<Pokemon/>);
    expect(screen.getByText(/go next/i)).toBeDisabled();
    await userEvent.click(screen.getByText(/go next/i));
    expect(screen.getByText(/page 1 of/i)).toBeInTheDocument();
    await userEvent.click(screen.getByText(/go prev/i));
    expect(screen.getByText(/page 0 of/i)).toBeInTheDocument();
})