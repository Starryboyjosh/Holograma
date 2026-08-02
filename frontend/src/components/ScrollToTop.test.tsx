import { describe, expect, it, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter, Route, Routes, useNavigate } from 'react-router-dom';
import { ScrollToTop } from './ScrollToTop';

function NavButtons() {
  const navigate = useNavigate();
  return (
    <div>
      <button onClick={() => navigate('/settings')}>ir a settings</button>
      <button onClick={() => navigate({ pathname: '/', hash: '#hablar' })}>
        ir a hablar
      </button>
    </div>
  );
}

function setup(initialEntries: string[] = ['/']) {
  return render(
    <MemoryRouter initialEntries={initialEntries}>
      <ScrollToTop />
      <Routes>
        <Route path="/" element={<NavButtons />} />
        <Route path="/settings" element={<div>settings</div>} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('ScrollToTop', () => {
  beforeEach(() => {
    window.scrollTo = vi.fn();
  });

  it('hace scroll al inicio al cambiar de ruta', () => {
    setup();
    fireEvent.click(screen.getByText('ir a settings'));
    expect(window.scrollTo).toHaveBeenLastCalledWith(0, 0);
  });

  it('no re-dispara con cambios de hash dentro de la misma ruta', () => {
    setup();
    window.scrollTo.mockClear();
    fireEvent.click(screen.getByText('ir a hablar'));
    expect(window.scrollTo).not.toHaveBeenCalled();
  });

  it('monta al inicio en la primera ruta', () => {
    setup();
    expect(window.scrollTo).toHaveBeenCalledWith(0, 0);
  });
});
