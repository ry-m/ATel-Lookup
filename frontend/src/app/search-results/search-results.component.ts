import { BreakpointObserver, Breakpoints } from '@angular/cdk/layout';
import {
  Component,
  Input,
  OnChanges,
  QueryList,
  ViewChild,
  ViewChildren,
} from '@angular/core';
import { MatPaginator } from '@angular/material/paginator';
import { SearchResult } from '../search-result';
import { TelegramCardComponent } from '../telegram-card/telegram-card.component';

@Component({
  selector: 'app-search-results',
  templateUrl: './search-results.component.html',
  styleUrls: ['./search-results.component.scss'],
})
export class SearchResultsComponent implements OnChanges {
  @Input() public result?: SearchResult;

  @ViewChildren(TelegramCardComponent)
  cards?: QueryList<TelegramCardComponent>;

  @ViewChild(MatPaginator)
  paginator?: MatPaginator;

  public readonly pageSize = 10;

  public page = 0;

  public isSmall = false;

  constructor(private breakpointObserver: BreakpointObserver) {
    this.breakpointObserver
      .observe([
        Breakpoints.XSmall,
        Breakpoints.Small,
        Breakpoints.Medium,
        Breakpoints.Large,
        Breakpoints.XLarge,
      ])
      .subscribe(() => this.setIsSmall());
  }

  get view() {
    const index = this.page * this.pageSize;
    return this.result?.telegrams?.slice(index, index + this.pageSize);
  }

  setIsSmall() {
    this.isSmall =
      this.breakpointObserver.isMatched(Breakpoints.XSmall) ||
      this.breakpointObserver.isMatched(Breakpoints.Small);
  }

  ngOnChanges() {
    this.updatePage(0);
  }

  top() {
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  scrollToTelegram(id: number) {
    const page = this.getPageForTelegram(id);
    this.updatePage(page);

    setTimeout(() => {
      this.cards?.forEach((card) => {
        if (card.telegram?.id === id) {
          card.scroll();
        }
      });
    });
  }

  updatePage(page: number) {
    this.page = page;
    if (this.paginator) {
      this.paginator.pageIndex = this.page;
    }
    this.cards?.first.scroll();
  }

  getPageForTelegram(id: number) {
    const index =
      this.result?.telegrams.findIndex((telegram) => telegram.id === id) || 0;
    const page = Math.floor(index / this.pageSize);
    return page;
  }
}
